"""Unit tests for evals.harness.regression (ADR-003 §3,4,6; Task 024)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evals.harness.driver import EvalRunRecord
from evals.harness.metrics import MaxStepsMetric
from evals.harness.regression import (
    ProbeScopedMetric,
    RegressionSelectionError,
    _runnable,
    _select_probes,
    experiment_config,
    run_probe,
    run_regression,
)
from evals.regression.probe import RegressionProbe


def test_probe_scoped_metric() -> None:
    inner = MaxStepsMetric()
    scoped = ProbeScopedMetric("target-probe", inner)

    # Different probe_id returns empty list (0 scores)
    assert scoped.score(probe_id="other-probe", steps=1, max_steps=5) == []

    # Matching probe_id delegates to inner metric
    result = scoped.score(probe_id="target-probe", steps=1, max_steps=5)
    assert result.value == 1.0


def test_select_probes() -> None:
    p1 = RegressionProbe("p1", "prompt 1", lambda w: None, [MaxStepsMetric()])
    p2 = RegressionProbe("p2", "prompt 2", lambda w: None, [MaxStepsMetric()])

    assert len(_select_probes([p1, p2], probe_id=None)) == 2
    assert _select_probes([p1, p2], probe_id="p1") == [p1]
    assert _select_probes([p1, p2], probe_id="unknown") == []


def test_runnable_filters_skipped_probes() -> None:
    p_runnable = RegressionProbe("p1", "prompt 1", lambda w: None, [MaxStepsMetric()])
    p_skipped = RegressionProbe(
        "p2",
        "prompt 2",
        lambda w: None,
        [MaxStepsMetric()],
        skip_reason="feature not ready",
    )

    runnable = _runnable([p_runnable, p_skipped])
    assert runnable == [p_runnable]


def test_experiment_config() -> None:
    config = experiment_config()
    assert config["provider"] == "gemini"
    assert config["harness"] == "regression"
    assert "agent_model" in config
    assert "git_sha" in config


def test_run_probe_happy_path() -> None:
    probe = RegressionProbe(
        id="test-probe",
        prompt="Hello agent",
        fixture=lambda w: (w / "test.txt").write_text("content", encoding="utf-8"),
        metrics=[MaxStepsMetric()],
        max_requests=5,
    )

    fake_record = EvalRunRecord(
        output="I see test.txt",
        messages=[],
        tool_calls=[],
        steps=1,
        input_tokens=10,
        output_tokens=5,
        denied_tools=[],
        error=None,
    )

    with patch("evals.harness.regression.run_agent_once_sync", return_value=fake_record):
        payload = run_probe(probe)

    assert payload["output"] == "I see test.txt"
    assert payload["steps"] == 1
    assert payload["input_tokens"] == 10
    assert payload["output_tokens"] == 5
    assert payload["probe_id"] == "test-probe"
    assert "test.txt" in payload["file_state"]
    assert payload["file_state"]["test.txt"] == "content"
    assert payload["agent_error"] is None
    assert payload["infra_error"] is None


def test_run_regression_no_matching_probes() -> None:
    with pytest.raises(RegressionSelectionError, match="no runnable regression probe matched"):
        run_regression(probe_id="non-existent-probe-123")


def test_run_regression_mocked_opik() -> None:
    mock_eval_result = MagicMock()

    with (
        patch("opik.Opik"),
        patch("evals.harness.regression.load_probes") as mock_load,
        patch("evals.harness.datasets.sync_regression_dataset") as mock_sync,
        patch("opik.evaluation.evaluate", return_value=mock_eval_result) as mock_eval,
    ):
        mock_probe = MagicMock(spec=RegressionProbe)
        mock_probe.id = "01-smoke"
        mock_probe.metrics = [MaxStepsMetric()]
        mock_probe.skip_reason = None
        mock_load.return_value = [mock_probe]

        mock_dataset = MagicMock()
        mock_dataset.get_items.return_value = [{"id": "item-1", "probe_id": "01-smoke"}]
        mock_sync.return_value = mock_dataset

        result = run_regression(probe_id="01-smoke")

        assert result == mock_eval_result
        mock_eval.assert_called_once()
        kwargs = mock_eval.call_args[1]
        assert kwargs["task_threads"] == 1
        assert kwargs["experiment_config"]["provider"] == "gemini"
        assert kwargs["experiment_config"]["harness"] == "regression"
