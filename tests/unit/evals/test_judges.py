"""Unit tests for :mod:`evals.harness.judges` (ADR-003 §7; task 021).

Tests judge model resolution, Groq routing, overrides, and credential validation without live calls.
"""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opik.evaluation.metrics.llm_judges.g_eval.metric import GEvalScoreFormat
from opik.evaluation.models.litellm.litellm_chat_model import LiteLLMChatModel
from pydantic import SecretStr

from evals.harness.judges import (
    DEFAULT_GROQ_JUDGE,
    LIGHTWEIGHT_GROQ_JUDGE,
    ForgeGEval,
    GroqLiteLLMChatModel,
    MissingJudgeCredentialsError,
    judge_model,
    make_judge,
    resolve_judge_model,
    validate_judge_credentials,
)
from forge.config.settings import settings


def test_default_judge_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no override is provided, judge_model() defaults to groq/openai/gpt-oss-120b."""
    monkeypatch.setattr(settings, "eval_judge_model", "")
    assert judge_model() == DEFAULT_GROQ_JUDGE
    assert resolve_judge_model() == DEFAULT_GROQ_JUDGE


def test_judge_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """EVAL_JUDGE_MODEL override takes precedence, e.g. for lightweight groq model."""
    monkeypatch.setattr(settings, "eval_judge_model", LIGHTWEIGHT_GROQ_JUDGE)
    assert judge_model() == LIGHTWEIGHT_GROQ_JUDGE
    assert resolve_judge_model() == LIGHTWEIGHT_GROQ_JUDGE


def test_validate_judge_credentials_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation succeeds when GROQ_API_KEY is present in settings or env."""
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("test-groq-key"))
    validate_judge_credentials()  # should not raise


def test_validate_judge_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation raises MissingJudgeCredentialsError when GROQ_API_KEY is absent."""
    monkeypatch.setattr(settings, "groq_api_key", SecretStr(""))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(MissingJudgeCredentialsError, match="GROQ_API_KEY is required"):
        validate_judge_credentials()


def test_make_judge_constructs_geval() -> None:
    """make_judge constructs a GEval instance with specified introduction and rubric."""
    judge = make_judge(
        task_introduction="Judge code quality",
        evaluation_criteria="The code must be clean and minimal.",
    )
    assert judge.task_introduction == "Judge code quality"
    assert judge.evaluation_criteria == "The code must be clean and minimal."
    model = getattr(judge, "_model", getattr(judge, "model", None))
    model_name = getattr(model, "model_name", str(model))
    assert model_name == DEFAULT_GROQ_JUDGE
    assert isinstance(model, GroqLiteLLMChatModel)
    assert judge._log_probs_supported is False


def test_groq_litellm_model_excludes_logprobs() -> None:
    """GroqLiteLLMChatModel reports logprobs and top_logprobs as unsupported."""
    model = GroqLiteLLMChatModel(model_name=DEFAULT_GROQ_JUDGE)
    params = model.supported_params
    assert "logprobs" not in params
    assert "top_logprobs" not in params


def test_groq_litellm_model_generate_provider_response_transforms_kwargs() -> None:
    """GroqLiteLLMChatModel strips logprobs and converts Pydantic response_format to json_object."""
    model = GroqLiteLLMChatModel(model_name=DEFAULT_GROQ_JUDGE)
    with patch.object(model, "_litellm_completion") as mock_comp:
        mock_comp.return_value = MagicMock()
        model.generate_provider_response(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
            top_logprobs=20,
            response_format=GEvalScoreFormat,
        )
        mock_comp.assert_called_once()
        _, kwargs = mock_comp.call_args
        assert "logprobs" not in kwargs
        assert "top_logprobs" not in kwargs
        assert kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_groq_litellm_model_agenerate_provider_response_transforms_kwargs() -> None:
    """Async variant strips logprobs and converts Pydantic response_format to json_object."""
    model = GroqLiteLLMChatModel(model_name=DEFAULT_GROQ_JUDGE)
    with patch.object(model, "_litellm_acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = MagicMock()
        await model.agenerate_provider_response(
            messages=[{"role": "user", "content": "hi"}],
            logprobs=True,
            top_logprobs=20,
            response_format=GEvalScoreFormat,
        )
        mock_acomp.assert_called_once()
        _, kwargs = mock_acomp.call_args
        assert "logprobs" not in kwargs
        assert "top_logprobs" not in kwargs
        assert kwargs["response_format"] == {"type": "json_object"}


def test_forge_geval_retries_on_logprobs_error() -> None:
    """ForgeGEval catches logprobs-related BaseLLMError, disables logprobs, and retries."""
    judge = ForgeGEval(
        task_introduction="intro",
        evaluation_criteria="criteria",
        model="gpt-4o",
    )
    judge._log_probs_supported = True

    calls = 0

    def mock_super_score(output: str, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("BadRequestError: logprobs is not supported with this model")
        return MagicMock(name="score_result")

    with patch("opik.evaluation.metrics.GEval.score", side_effect=mock_super_score):
        res = judge.score("test output")
        assert calls == 2
        assert judge._log_probs_supported is False
        assert res is not None


def test_forge_geval_reraises_other_errors() -> None:
    """ForgeGEval does not hide evaluation failures that are unrelated to logprobs."""
    judge = ForgeGEval(
        task_introduction="intro",
        evaluation_criteria="criteria",
        model="gpt-4o",
    )
    judge._log_probs_supported = False

    with (
        patch("opik.evaluation.metrics.GEval.score", side_effect=ValueError("RateLimit exceeded")),
        pytest.raises(ValueError, match="RateLimit exceeded"),
    ):
        judge.score("test output")


def test_forge_geval_formats_input_and_file_state() -> None:
    """ForgeGEval prefixes agent output and appends file_state for LLM judges."""
    judge = ForgeGEval(
        task_introduction="intro",
        evaluation_criteria="criteria",
        model="gpt-4o",
    )
    captured_output = ""

    def mock_super_score(output: str, **kwargs: object) -> object:
        nonlocal captured_output
        captured_output = output
        return MagicMock(name="score_result")

    with patch("opik.evaluation.metrics.GEval.score", side_effect=mock_super_score):
        judge.score("sample output", file_state={"foo.py": "x = 1"})
        assert "[Agent Response to be Evaluated]:" in captured_output
        assert "sample output" in captured_output
        assert "[File State]:" in captured_output
        assert "foo.py:" in captured_output
        assert "x = 1" in captured_output


def test_groq_model_retries_on_rate_limit() -> None:
    """GroqLiteLLMChatModel catches rate limit errors and retries after sleeping."""
    model = GroqLiteLLMChatModel("groq/openai/gpt-oss-120b")
    calls = 0

    def mock_super_gen(messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("Rate limit reached: Please try again in 0.1s")
        return MagicMock(name="response")

    with (
        patch.object(LiteLLMChatModel, "generate_provider_response", side_effect=mock_super_gen),
        patch("time.sleep") as mock_sleep,
    ):
        res = model.generate_provider_response([{"role": "user", "content": "hi"}])
        assert calls == 2
        assert mock_sleep.call_count == 1
        assert res is not None


def test_groq_model_ignores_deprecation_warning() -> None:
    """GroqLiteLLMChatModel suppresses DeprecationWarning from httpx/litellm."""
    model = GroqLiteLLMChatModel("groq/openai/gpt-oss-120b")

    def mock_super_gen(messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        warnings.warn(
            "Use 'content=<...>' to upload raw bytes/text content.",
            DeprecationWarning,
            stacklevel=2,
        )
        return MagicMock(name="response")

    with patch.object(LiteLLMChatModel, "generate_provider_response", side_effect=mock_super_gen):
        res = model.generate_provider_response([{"role": "user", "content": "hi"}])
        assert res is not None
