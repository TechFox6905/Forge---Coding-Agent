"""Unit tests for :mod:`evals.harness.driver` (ADR-003 §4; task 020).

All tests run offline using ``FunctionModel`` or ``TestModel`` — no network or credentials needed.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from pydantic import SecretStr
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from pydantic_ai.models.test import TestModel

from evals.harness.driver import (
    CAP_STOP_TEXT,
    ToolCallRecord,
    _build_record,
    run_agent_once,
    run_agent_once_sync,
)
from forge.agent.factory import build_agent
from forge.entities.permissions import PermissionDecision, PermissionRequest


@pytest.fixture(autouse=True)
def dummy_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure build_agent() constructs cleanly without requiring a real GEMINI_API_KEY."""
    monkeypatch.setattr("forge.agent.factory.settings.gemini_api_key", SecretStr("test-key"))


def test_build_record_extracts_tool_calls_and_tokens() -> None:
    """Verify tool call extraction and token usage aggregation from message history."""
    call_part = ToolCallPart(
        tool_name="read",
        args={"path": "hello.txt"},
        tool_call_id="call_1",
    )
    return_part = ToolReturnPart(
        tool_name="read",
        content="hello world",
        tool_call_id="call_1",
        outcome="success",
    )
    denied_return_part = ToolReturnPart(
        tool_name="bash",
        content="permission denied",
        tool_call_id="call_2",
        outcome="denied",
    )

    response1 = ModelResponse(
        parts=[call_part],
        model_name="test-model",
    )
    response1.usage.input_tokens = 50
    response1.usage.output_tokens = 20

    request_msg = ModelRequest(parts=[return_part, denied_return_part])

    response2 = ModelResponse(
        parts=[TextPart(content="Task completed successfully.")],
        model_name="test-model",
    )
    response2.usage.input_tokens = 60
    response2.usage.output_tokens = 15

    messages: list[ModelMessage] = [response1, request_msg, response2]

    record = _build_record(messages)

    assert record.output == "Task completed successfully."
    assert record.steps == 2
    assert record.input_tokens == 110
    assert record.output_tokens == 35
    assert len(record.tool_calls) == 1
    assert record.tool_calls[0] == ToolCallRecord(name="read", args={"path": "hello.txt"})
    assert record.denied_tools == ["bash"]
    assert record.error is None
    assert record.agent_error is None


@pytest.mark.asyncio
async def test_run_agent_once_basic_turn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run real agent stack with TestModel returning plain text."""
    agent = build_agent()
    with agent.override(model=TestModel(call_tools=[], custom_output_text="I am Forge.")):
        monkeypatch.setattr("evals.harness.driver.build_agent", lambda: agent)
        record = await run_agent_once("Who are you?", cwd=tmp_path)

    assert record.output == "I am Forge."
    assert record.steps >= 1
    assert record.error is None


@pytest.mark.asyncio
async def test_run_agent_once_headless_permission_auto_deny(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default headless execution denies permission requests when gate_mode is ask."""
    file_to_write = tmp_path / "test.txt"
    state = {"calls": 0}

    async def stream_function(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        state["calls"] += 1
        if state["calls"] == 1:
            yield {
                0: DeltaToolCall(
                    name="write",
                    json_args=json.dumps({"path": str(file_to_write), "content": "forbidden"}),
                )
            }
        else:
            yield "I could not write the file."

    agent = build_agent()
    with agent.override(model=FunctionModel(stream_function=stream_function)):
        monkeypatch.setattr("evals.harness.driver.build_agent", lambda: agent)
        record = await run_agent_once(
            "Write the file",
            cwd=tmp_path,
            gate_mode="ask",
        )

    assert "write" in record.denied_tools
    assert not file_to_write.exists()


@pytest.mark.asyncio
async def test_run_agent_once_bypass_auto_allows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bypass mode auto-allows gated tools."""
    file_to_write = tmp_path / "hello.txt"
    state = {"calls": 0}

    async def stream_function(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        state["calls"] += 1
        if state["calls"] == 1:
            yield {
                0: DeltaToolCall(
                    name="write",
                    json_args=json.dumps({"path": str(file_to_write), "content": "hello world"}),
                )
            }
        else:
            yield "File written."

    agent = build_agent()
    with agent.override(model=FunctionModel(stream_function=stream_function)):
        monkeypatch.setattr("evals.harness.driver.build_agent", lambda: agent)
        record = await run_agent_once(
            "Write the file",
            cwd=tmp_path,
            gate_mode="bypass",
        )

    assert file_to_write.exists()
    assert file_to_write.read_text(encoding="utf-8") == "hello world"
    assert "write" not in record.denied_tools


@pytest.mark.asyncio
async def test_run_agent_once_custom_permission_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A custom resolver can allow or deny specific tool calls."""
    allowed_file = tmp_path / "allowed.txt"

    async def custom_resolver(req: PermissionRequest) -> PermissionDecision:
        if req.tool_name == "write" and "allowed.txt" in req.args:
            return PermissionDecision.allow()
        return PermissionDecision.deny(reason="custom deny")

    state = {"calls": 0}

    async def stream_function(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        state["calls"] += 1
        if state["calls"] == 1:
            yield {
                0: DeltaToolCall(
                    name="write",
                    json_args=json.dumps({"path": str(allowed_file), "content": "ok"}),
                )
            }
        else:
            yield "Done."

    agent = build_agent()
    with agent.override(model=FunctionModel(stream_function=stream_function)):
        monkeypatch.setattr("evals.harness.driver.build_agent", lambda: agent)
        record = await run_agent_once(
            "Write allowed file",
            cwd=tmp_path,
            resolve_permission=custom_resolver,
        )
        assert record.output is not None

    assert allowed_file.exists()
    assert allowed_file.read_text(encoding="utf-8") == "ok"


@pytest.mark.asyncio
async def test_run_agent_once_max_requests_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When max_requests is exceeded, the capped model stops with CAP_STOP_TEXT."""
    counter = 0

    async def stream_function(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        nonlocal counter
        counter += 1
        yield {0: DeltaToolCall(name="glob", json_args='{"pattern": "*"}')}

    agent = build_agent()
    with agent.override(model=FunctionModel(stream_function=stream_function)):
        monkeypatch.setattr("evals.harness.driver.build_agent", lambda: agent)
        record = await run_agent_once(
            "Loop forever",
            cwd=tmp_path,
            gate_mode="bypass",
            max_requests=2,
        )

    assert CAP_STOP_TEXT in record.output


def test_run_agent_once_sync_wrapper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """run_agent_once_sync wraps run_agent_once in asyncio.run."""
    agent = build_agent()
    with agent.override(model=TestModel(call_tools=[], custom_output_text="sync test")):
        monkeypatch.setattr("evals.harness.driver.build_agent", lambda: agent)
        record = run_agent_once_sync("Test sync", cwd=tmp_path)

    assert record.output == "sync test"
