"""Unit tests for evals.harness.benchmark and evals.benchmark.runner (ADR-003 §3,4,8; Task 023)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evals.benchmark.runner import (
    BenchmarkSelectionError,
    agent_model,
    experiment_config,
    git_sha,
    make_benchmark_task_fn,
    run_benchmark,
)
from evals.harness.driver import EvalRunRecord
from evals.harness.task_loader import BenchmarkTask


def test_experiment_config() -> None:
    config = experiment_config(sandbox="local")
    assert config["provider"] == "gemini"
    assert config["sandbox"] == "local"
    assert "agent_model" in config
    assert "git_sha" in config


def test_git_sha() -> None:
    sha = git_sha()
    assert isinstance(sha, str)
    assert len(sha) > 0


def test_agent_model() -> None:
    model = agent_model()
    assert isinstance(model, str)
    assert "gemini" in model.lower()


def test_run_benchmark_invalid_trials() -> None:
    with pytest.raises(ValueError, match="trials must be >= 1"):
        run_benchmark(trials=0)


def test_run_benchmark_no_matching_task() -> None:
    with pytest.raises(BenchmarkSelectionError, match="no benchmark task matched"):
        run_benchmark(task_id="definitely-non-existent-task-id-12345")


def test_make_benchmark_task_fn(tmp_path: Path) -> None:
    task_dir = tmp_path / "mock-task"
    task_dir.mkdir()
    (task_dir / "setup").mkdir()
    (task_dir / "solution").mkdir()
    verify_dir = task_dir / "verify"
    verify_dir.mkdir()
    (verify_dir / "verify.sh").write_text("echo PASS; exit 0", encoding="utf-8")

    task = BenchmarkTask(
        id="mock-task",
        prompt="Do nothing",
        max_steps=3,
        difficulty="easy",
        task_dir=task_dir,
    )

    fake_record = EvalRunRecord(
        output="Done!",
        messages=[],
        tool_calls=[],
        steps=1,
        input_tokens=10,
        output_tokens=5,
        denied_tools=[],
        error=None,
    )

    with patch("evals.harness.benchmark.run_agent_once_sync", return_value=fake_record):
        task_fn = make_benchmark_task_fn({"mock-task": task}, sandbox="local")
        payload = task_fn({"task_id": "mock-task"})

    assert payload["output"] == "Done!"
    assert payload["steps"] == 1
    assert payload["input_tokens"] == 10
    assert payload["output_tokens"] == 5
    assert payload["verify"]["exit_code"] == 0
    assert "PASS" in payload["verify"]["stdout"]
    assert payload["agent_error"] is None
    assert payload["infra_error"] is None


def test_run_benchmark_mocked_opik() -> None:
    mock_eval_result = MagicMock()
    mock_eval_result.test_results = []

    with (
        patch("opik.Opik"),
        patch("evals.harness.benchmark.load_benchmark_tasks") as mock_load,
        patch("evals.harness.datasets.sync_benchmark_dataset") as mock_sync,
        patch("opik.evaluation.evaluate", return_value=mock_eval_result) as mock_eval,
        patch("evals.harness.benchmark._attach_aggregates") as mock_attach,
    ):
        mock_task = MagicMock(spec=BenchmarkTask)
        mock_task.id = "001-find-and-replace"
        mock_task.difficulty = "easy"
        mock_task.judges = []
        mock_load.return_value = [mock_task]

        mock_dataset = MagicMock()
        mock_dataset.get_items.return_value = [{"id": "item-1", "task_id": "001-find-and-replace"}]
        mock_sync.return_value = mock_dataset

        result = run_benchmark(task_id="001-find-and-replace", trials=2)

        assert result == mock_eval_result
        mock_eval.assert_called_once()
        kwargs = mock_eval.call_args[1]
        assert kwargs["task_threads"] == 1
        assert kwargs["trial_count"] == 2
        assert kwargs["experiment_config"]["provider"] == "gemini"
        mock_attach.assert_called_once()
