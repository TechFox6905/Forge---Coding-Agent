"""The G-Eval judge factory — LLM judges for what code cannot score (ADR-003 §7; task 021).

Judges are reserved for quality / groundedness / minimal-diff style grading; everything mechanical
stays a :class:`~opik.evaluation.metrics.base_metric.BaseMetric` in ``metrics.py``. One factory,
:func:`make_judge`, builds an Opik :class:`~opik.evaluation.metrics.GEval` routed to Groq through
LiteLLM (ADR-003 §7): :func:`judge_model` resolves the LiteLLM model string —
``EVAL_JUDGE_MODEL`` overrides, else the default is ``DEFAULT_GROQ_JUDGE`` (``groq/openai/gpt-oss-120b``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import warnings
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from typing import Any

from opik.evaluation.metrics import GEval, score_result
from opik.evaluation.metrics.llm_judges.g_eval.metric import GEvalScoreFormat
from opik.evaluation.models.litellm.litellm_chat_model import LiteLLMChatModel

from forge.config.settings import settings

logger = logging.getLogger(__name__)

# The default judge model routed via LiteLLM to Groq (ADR-003 §7)
DEFAULT_GROQ_JUDGE = "groq/openai/gpt-oss-120b"
LIGHTWEIGHT_GROQ_JUDGE = "groq/openai/gpt-oss-20b"


class MissingJudgeCredentialsError(Exception):
    """Raised when GROQ_API_KEY is missing but a live judge call or validation requires it."""


class GroqLiteLLMChatModel(LiteLLMChatModel):
    """LiteLLMChatModel adapted for Groq and models that do not support logprobs.

    Root causes handled:
    1. LiteLLM's ``get_supported_openai_params(model="groq/...")`` reports ``logprobs`` and ``top_logprobs``
       as supported parameters.
    2. Opik's ``GEval._init_model`` inspects ``model.supported_params``; seeing ``logprobs`` and ``top_logprobs``,
       it sets ``_log_probs_supported = True``.
    3. When scoring, Opik passes ``logprobs=True, top_logprobs=20`` in ``provider_kwargs``.
    4. Groq's API rejects ``logprobs`` with HTTP 400 Bad Request:
       ``{"error":{"message":"`logprobs` is not supported with this model","type":"invalid_request_error","param":"logprobs"}}``.
    5. When LiteLLM is given a Pydantic model for ``response_format`` with Groq, it attempts to use tool calling /
       function calling emulation, which fails if the model emits plain JSON text instead of a tool call.
       Supplying ``response_format={"type": "json_object"}`` instructs Groq's engine to emit valid JSON natively.

    This class:
    - Discards ``logprobs`` and ``top_logprobs`` from ``supported_params``, so Opik's ``GEval`` correctly recognizes
      that logprobs are not supported (``_log_probs_supported = False``).
    - Drops any ``logprobs`` / ``top_logprobs`` keyword arguments before calling LiteLLM.
    - Converts Pydantic ``response_format`` (like ``GEvalScoreFormat``) to ``{"type": "json_object"}`` so Groq
      enforces native JSON object generation without brittle tool-call emulation.
    """

    @property
    def supported_params(self) -> AbstractSet[str]:
        """Set of supported parameters without logprobs/top_logprobs for Groq."""
        params = set(super().supported_params)
        params.discard("logprobs")
        params.discard("top_logprobs")
        return params

    def generate_provider_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        kwargs.pop("logprobs", None)
        kwargs.pop("top_logprobs", None)
        if kwargs.get("response_format") == GEvalScoreFormat:
            kwargs["response_format"] = {"type": "json_object"}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    return super().generate_provider_response(messages, **kwargs)
            except Exception as exc:
                err_str = str(exc)
                if (
                    any(term in err_str.lower() for term in ("rate limit", "429", "tpm", "rpm"))
                    and attempt < max_retries - 1
                ):
                    match = re.search(r"try again in ([\d\.]+)s", err_str)
                    wait_time = float(match.group(1)) + 1.0 if match else 10.0
                    logger.warning(
                        "Groq rate limit reached; waiting %.1fs before retry (%d/%d): %s",
                        wait_time,
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    time.sleep(wait_time)
                    continue
                raise

    async def agenerate_provider_response(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> Any:
        kwargs.pop("logprobs", None)
        kwargs.pop("top_logprobs", None)
        if kwargs.get("response_format") == GEvalScoreFormat:
            kwargs["response_format"] = {"type": "json_object"}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    return await super().agenerate_provider_response(messages, **kwargs)
            except Exception as exc:
                err_str = str(exc)
                if (
                    any(term in err_str.lower() for term in ("rate limit", "429", "tpm", "rpm"))
                    and attempt < max_retries - 1
                ):
                    match = re.search(r"try again in ([\d\.]+)s", err_str)
                    wait_time = float(match.group(1)) + 1.0 if match else 10.0
                    logger.warning(
                        "Groq rate limit reached; waiting %.1fs before retry (%d/%d): %s",
                        wait_time,
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise


class ForgeGEval(GEval):
    """GEval judge that handles unsupported logprobs robustly without hiding evaluation failures.

    If a provider rejects logprobs despite configuration, this judge disables logprobs and retries
    the scoring call once. Real evaluation failures (invalid scores, API errors, rate limits) are
    never swallowed and are raised immediately.

    Also formats the evaluated input with explicit labels and includes ``file_state`` when provided
    in kwargs, so LLM judges have full context to evaluate file-modification and groundedness criteria.
    """

    def _prepare_evaluation_input(self, output: str, kwargs: Mapping[str, Any]) -> str:
        parts: list[str] = [f"[Agent Response to be Evaluated]:\n{output}"]
        file_state = kwargs.get("file_state")
        if file_state and isinstance(file_state, dict):
            files_desc = "\n".join(f"{path}:\n{content}" for path, content in file_state.items())
            parts.append(f"\n[File State]:\n{files_desc}")
        return "\n".join(parts)

    def score(self, output: str, **ignored_kwargs: Any) -> score_result.ScoreResult:
        formatted_input = self._prepare_evaluation_input(output, ignored_kwargs)
        try:
            return super().score(formatted_input, **ignored_kwargs)
        except Exception as exc:
            if self._log_probs_supported and "logprobs" in str(exc).lower():
                logger.warning(
                    "Model provider rejected logprobs; retrying G-Eval without logprobs: %s", exc
                )
                self._log_probs_supported = False
                return super().score(formatted_input, **ignored_kwargs)
            raise

    async def ascore(self, output: str, **ignored_kwargs: Any) -> score_result.ScoreResult:
        formatted_input = self._prepare_evaluation_input(output, ignored_kwargs)
        try:
            return await super().ascore(formatted_input, **ignored_kwargs)
        except Exception as exc:
            if self._log_probs_supported and "logprobs" in str(exc).lower():
                logger.warning(
                    "Model provider rejected logprobs; retrying G-Eval without logprobs: %s", exc
                )
                self._log_probs_supported = False
                return await super().ascore(formatted_input, **ignored_kwargs)
            raise


def judge_model() -> str:
    """Resolve the LiteLLM model string the G-Eval judge runs on (ADR-003 §7).

    An explicit ``settings.eval_judge_model`` (``EVAL_JUDGE_MODEL``) wins verbatim (whitespace-only
    is treated as unset). Otherwise the default is :data:`DEFAULT_GROQ_JUDGE`.
    Pure and network-free — safe to unit-test without keys.
    """
    override = settings.eval_judge_model.strip()
    if override:
        return override
    return DEFAULT_GROQ_JUDGE


def resolve_judge_model() -> str:
    """The judge model identifier every Opik metric factory feeds to its ``model=`` slot (ADR-003 §7)."""
    return judge_model()


def validate_judge_credentials() -> None:
    """Ensure GROQ_API_KEY is available in settings or environment; raise if missing."""
    groq_key = (
        settings.groq_api_key.get_secret_value().strip()
        or os.environ.get("GROQ_API_KEY", "").strip()
    )
    if not groq_key:
        raise MissingJudgeCredentialsError(
            "GROQ_API_KEY is required for evaluation judges (see .env.example)."
        )


def make_judge(
    task_introduction: str,
    evaluation_criteria: str,
    model: str | None = None,
) -> GEval:
    """Build a G-Eval judge carrying the model :func:`resolve_judge_model` resolved (ADR-003 §7).

    ``task_introduction`` frames what the judge is grading; ``evaluation_criteria`` is the rubric.
    The model comes from ``model`` or :func:`resolve_judge_model` (routed through LiteLLM to Groq).
    Construction makes no LLM call.
    """
    model_id = model or resolve_judge_model()
    if "groq" in model_id.lower():
        chat_model = GroqLiteLLMChatModel(model_name=model_id)
        judge = ForgeGEval(
            task_introduction=task_introduction,
            evaluation_criteria=evaluation_criteria,
            model=chat_model,
        )
        judge._log_probs_supported = False
        return judge

    return ForgeGEval(
        task_introduction=task_introduction,
        evaluation_criteria=evaluation_criteria,
        model=model_id,
    )
