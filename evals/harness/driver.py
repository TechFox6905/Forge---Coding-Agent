"""The one in-process agent driver every eval track reuses (ADR-003 §4).

:func:`run_agent_once` drives the REAL ``build_agent()`` + ``AgentDeps`` + ``AgentTurnHandler`` +
``Runner`` — the exact stack ``tests/integration/test_milestone1_capstone.py`` proves — submits one
prompt, and drives it to idle. What comes back is an :class:`EvalRunRecord` read entirely from the
pydantic-ai message history: tool calls from ``ToolCallPart``s, usage summed from each
``ModelResponse.usage``. Grading never parses Opik traces (that would couple it to the
observability pipeline and lie under export lag).

Configurable per probe/benchmark: the gate mode, permission rules, custom permission / question
resolvers (default = headless auto-deny), a pre-filled ``message_history``, and ``max_requests`` —
a hard cap on model requests so a runaway run stops gracefully instead of burning budget.
:func:`run_agent_once_sync` wraps it in :func:`asyncio.run` because Opik ``evaluate()`` task fns
cannot be async.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.wrapper import WrapperModel

from forge.agent.deps import AgentDeps
from forge.agent.factory import build_agent
from forge.agent.loop import AgentTurnHandler
from forge.entities import events
from forge.entities.permissions import PermissionDecision, PermissionRequest
from forge.harness.runner import Runner
from forge.permissions.gate import PermissionGate
from forge.tools.askuser import deny_user_question_resolver
from forge.tui.app import InputIntent

if TYPE_CHECKING:
    from pydantic_ai.models import Model, ModelRequestParameters
    from pydantic_ai.settings import ModelSettings

logger = logging.getLogger(__name__)

# The text the request cap substitutes for the model's next call once the cap is reached, so the
# agent loop ends on a plain-text output (a graceful stop) instead of running forever.
CAP_STOP_TEXT = "Eval run stopped: reached the max model-request cap."


PermissionResolver = Callable[[PermissionRequest], Awaitable[PermissionDecision]]
UserQuestionResolver = Callable[[str], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """One tool call the agent made: the tool name and its arguments (ADR-003 §4).

    ``args`` is the decoded argument mapping when the ``ToolCallPart`` carries structured args, else
    the raw JSON string the model streamed — extracted from the message history, never a trace.
    """

    name: str
    args: dict[str, Any] | str


@dataclass(frozen=True, slots=True)
class EvalRunRecord:
    """Everything an eval metric needs about one run, read from the message history (ADR-003 §4).

    * ``output`` — the agent's final assistant text.
    * ``messages`` — the whole pydantic-ai conversation (prior history + this run).
    * ``tool_calls`` — every ``ToolCallPart``, in order, as name + args.
    * ``steps`` — the model-request count (one per ``ModelResponse``).
    * ``input_tokens`` / ``output_tokens`` — summed from each ``ModelResponse.usage`` (the
      message-history equivalent of ``result.usage()``).
    * ``denied_tools`` — the tools the gate denied (``ToolReturnPart.outcome == "denied"``).
    * ``error`` — the error message if the turn crashed or failed, else ``None``.
    * ``compaction_events`` — count of compaction events emitted (0 for v1).
    """

    output: str
    messages: list[ModelMessage]
    tool_calls: list[ToolCallRecord]
    steps: int
    input_tokens: int
    output_tokens: int
    denied_tools: list[str] = field(default_factory=list)
    error: str | None = None
    compaction_events: int = 0

    @property
    def agent_error(self) -> str | None:
        """Alias for error for compatibility with benchmark / regression consumers."""
        return self.error


async def _deny_permission_resolver(request: PermissionRequest) -> PermissionDecision:
    """The headless auto-deny default (ADR-003 §4).

    An eval run has no interactive approver by default, so an ``ASK`` the probe did not override is
    denied — the safe default. Callers/probes that want approval supply their own ``resolve_permission``.
    """
    logger.debug("eval driver denying permission for tool=%s", request.tool_name)
    return PermissionDecision.deny(reason="No interactive approver in the eval harness.")


async def _allow_permission_resolver(request: PermissionRequest) -> PermissionDecision:
    """Auto-allow resolver for bypass execution (ADR-003 §3,4)."""
    logger.debug("eval driver allowing permission for tool=%s", request.tool_name)
    return PermissionDecision.allow()


def _cap_stop_stream() -> FunctionModel:
    """A one-shot :class:`FunctionModel` that streams :data:`CAP_STOP_TEXT` and nothing else.

    Substituted for the wrapped model once the request cap is hit, so the agent loop sees a
    plain-text response (no tool call) and stops on the next output — the graceful cap.
    """

    async def stream_function(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        yield CAP_STOP_TEXT

    async def call_function(messages: list[ModelMessage], info: AgentInfo) -> str:
        return CAP_STOP_TEXT

    return FunctionModel(function=call_function, stream_function=stream_function)


class _RequestCappedModel(WrapperModel):
    """Wrap a model, counting each generation and stopping gracefully past ``max_requests``.

    Each ``request_stream`` / ``request`` increments the counter; the first call beyond the cap
    delegates to :func:`_cap_stop_stream` instead of the wrapped model, so a runaway run ends on a
    plain-text response rather than crashing or burning budget.
    """

    def __init__(self, wrapped: Model, max_requests: int) -> None:
        super().__init__(wrapped)
        self._max_requests = max_requests
        self.request_count = 0
        self._stop_model = _cap_stop_stream()

    @asynccontextmanager
    async def request_stream(  # type: ignore[override]
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: Any = None,
    ) -> AsyncIterator[Any]:
        self.request_count += 1
        target = self._stop_model if self.request_count > self._max_requests else self.wrapped
        async with target.request_stream(
            messages, model_settings, model_request_parameters, run_context
        ) as stream:
            yield stream

    async def request(  # type: ignore[override]
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> Any:
        self.request_count += 1
        target = self._stop_model if self.request_count > self._max_requests else self.wrapped
        return await target.request(messages, model_settings, model_request_parameters)


async def run_agent_once(
    prompt: str,
    *,
    cwd: Path,
    gate_mode: Any = "bypass",
    permission_rules: Any = None,
    resolve_permission: PermissionResolver | None = None,
    resolve_user_question: UserQuestionResolver | None = None,
    message_history: list[ModelMessage] | None = None,
    max_requests: int | None = None,
    enable_compaction: bool = False,
) -> EvalRunRecord:
    """Drive one prompt through the real agent stack and return an :class:`EvalRunRecord` (ADR-003 §4).

    Builds the REAL ``build_agent()``, real :class:`~forge.agent.deps.AgentDeps`, a real
    :class:`~forge.agent.loop.AgentTurnHandler` seeded with ``message_history``, and a real
    :class:`~forge.harness.runner.Runner`; submits ``prompt`` and waits for idle.
    """
    agent = build_agent()
    gate = PermissionGate()
    errors: list[str] = []

    def _capture_emit(event: object) -> None:
        if isinstance(event, events.AgentError):
            errors.append(event.message)

    # Determine effective permission resolver:
    # 1. Custom resolver passed by caller wins.
    # 2. If gate_mode is "bypass" / "allow", auto-allow.
    # 3. Default to headless auto-deny.
    if resolve_permission is not None:
        effective_permission = resolve_permission
    elif gate_mode in ("bypass", "allow"):
        effective_permission = _allow_permission_resolver
    else:
        effective_permission = _deny_permission_resolver

    # If permission_rules are supplied and caller did not supply a custom resolver,
    # evaluate them if they implement a check/matches protocol
    if permission_rules is not None and resolve_permission is None:
        rules = permission_rules

        async def _rules_resolver(request: PermissionRequest) -> PermissionDecision:
            if hasattr(rules, "check"):
                decision = rules.check(request)
                if isinstance(decision, PermissionDecision):
                    return decision
            return await effective_permission(request)

        effective_permission = _rules_resolver

    deps = AgentDeps(
        cwd=cwd,
        emit=_capture_emit,
        gate=gate,
        resolve_permission=effective_permission,
        resolve_user_question=resolve_user_question or deny_user_question_resolver,
    )

    handler = AgentTurnHandler(
        agent,
        deps=deps,
        message_history=message_history,
    )
    runner = Runner(handler, on_event=_capture_emit)

    active_override = getattr(agent, "_override_model", None)
    if active_override is not None:
        override_val = active_override.get()
        current_model = getattr(override_val, "value", override_val) or agent.model
    else:
        current_model = agent.model
    cap = (
        agent.override(model=_RequestCappedModel(current_model, max_requests))
        if max_requests is not None
        else nullcontext()
    )
    try:
        with cap:
            await runner.submit(prompt, InputIntent.STEER)
            await runner.wait_idle()
    except Exception as exc:
        logger.exception("eval driver turn failed: %s", exc)
        errors.append(str(exc))

    return _build_record(
        handler.message_history,
        error=errors[0] if errors else None,
        compaction_events=0,
    )


def run_agent_once_sync(prompt: str, **kwargs: Any) -> EvalRunRecord:
    """Sync wrapper over :func:`run_agent_once` — Opik ``evaluate()`` task fns cannot be async."""
    return asyncio.run(run_agent_once(prompt, **kwargs))


def _build_record(
    messages: list[ModelMessage],
    *,
    error: str | None = None,
    compaction_events: int = 0,
) -> EvalRunRecord:
    """Assemble the :class:`EvalRunRecord` from the pydantic-ai message history (ADR-003 §4)."""
    tool_calls: list[ToolCallRecord] = []
    steps = 0
    input_tokens = 0
    output_tokens = 0
    for message in messages:
        if not isinstance(message, ModelResponse):
            continue
        steps += 1
        input_tokens += message.usage.input_tokens or 0
        output_tokens += message.usage.output_tokens or 0
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                tool_calls.append(ToolCallRecord(name=part.tool_name, args=_tool_args(part)))
    denied_tools = [
        part.tool_name
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart) and part.outcome == "denied"
    ]
    return EvalRunRecord(
        output=_final_text(messages),
        messages=list(messages),
        tool_calls=tool_calls,
        steps=steps,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        denied_tools=denied_tools,
        error=error,
        compaction_events=compaction_events,
    )


def _tool_args(part: ToolCallPart) -> dict[str, Any] | str:
    """The decoded argument mapping for a ``ToolCallPart``, or its raw JSON string if not a mapping."""
    args = part.args_as_dict()
    return args if isinstance(args, dict) else part.args_as_json_str()


def _final_text(messages: list[ModelMessage]) -> str:
    """The agent's final assistant text: the last ``ModelResponse`` that carries any ``TextPart``."""
    for message in reversed(messages):
        if not isinstance(message, ModelResponse):
            continue
        texts = [
            part.content for part in message.parts if isinstance(part, TextPart) and part.content
        ]
        if texts:
            return "".join(texts)
    return ""
