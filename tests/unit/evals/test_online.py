"""Unit tests for evals.harness.online (ADR-003 §8; Task 026)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from evals.harness.online import (
    CONVERSATION_METRIC_NAME,
    format_thread_scores,
    live_project_name,
    online_keys_missing,
    run_online_eval,
    trace_input_transform,
    trace_output_transform,
)
from forge.config.settings import settings


@dataclass
class DummyScore:
    name: str
    value: float
    scoring_failed: bool = False
    reason: str | None = None


@dataclass
class DummyThreadResult:
    thread_id: str
    scores: list[DummyScore]


@dataclass
class DummyThreadsEvaluationResult:
    results: list[DummyThreadResult]


def test_live_project_name() -> None:
    assert live_project_name() == settings.opik_project_name


def test_online_keys_missing() -> None:
    with patch("evals.harness.online.eval_keys_missing", return_value=["GEMINI_API_KEY"]):
        assert online_keys_missing() == ["GEMINI_API_KEY"]


def test_trace_transforms() -> None:
    # Bare string
    assert trace_input_transform("user input") == "user input"
    assert trace_output_transform("assistant reply") == "assistant reply"

    # Dict with text/output/content
    assert trace_input_transform({"content": "hello world"}) == "hello world"
    assert trace_output_transform({"output": "agent answer"}) == "agent answer"

    # Fallback to json string
    assert "data" in trace_input_transform({"data": 123})


def test_format_thread_scores() -> None:
    threads_res = DummyThreadsEvaluationResult(
        results=[
            DummyThreadResult(
                thread_id="t1",
                scores=[DummyScore(name=CONVERSATION_METRIC_NAME, value=0.9)],
            ),
            DummyThreadResult(
                thread_id="t2",
                scores=[
                    DummyScore(
                        name=CONVERSATION_METRIC_NAME,
                        value=0.0,
                        scoring_failed=True,
                        reason="timeout",
                    )
                ],
            ),
            DummyThreadResult(thread_id="t3", scores=[]),
        ]
    )

    lines = format_thread_scores(threads_res)  # type: ignore[arg-type]
    assert len(lines) == 3
    assert "t1: conversation_coherence=0.90" in lines[0]
    assert "t2: conversation_coherence=failed (timeout)" in lines[1]
    assert "t3: no scores" in lines[2]


def test_run_online_eval_mocked() -> None:
    mock_eval_res = DummyThreadsEvaluationResult(results=[])

    with (
        patch("evals.harness.online.make_conversation_metric") as mock_metric_fn,
        patch("opik.evaluation.evaluate_threads", return_value=mock_eval_res) as mock_eval,
    ):
        mock_metric_fn.return_value = MagicMock()
        result = run_online_eval(filter_string="start_time > 2026-01-01")

        assert result == mock_eval_res
        mock_eval.assert_called_once()
        kwargs = mock_eval.call_args[1]
        assert kwargs["project_name"] == settings.opik_project_name
        assert kwargs["filter_string"] == "start_time > 2026-01-01"
        assert kwargs["eval_project_name"] is None
