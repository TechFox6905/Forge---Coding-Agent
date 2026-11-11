"""Unit tests for evals.harness.aggregates (ADR-003 §8; Task 023)."""

from __future__ import annotations

from unittest.mock import MagicMock

from evals.harness.aggregates import (
    BenchmarkSummary,
    TaskAggregate,
    TrialOutcome,
    attach_experiment_aggregates,
    is_flaky,
    pass_at_1,
    pass_at_k,
    pass_hat_k,
    render_summary_table,
    summarize_outcomes,
)


def test_reliability_math_edge_cases() -> None:
    # Empty
    assert pass_at_1([]) == 0.0
    assert pass_at_k([]) == 0.0
    assert pass_hat_k([]) == 0.0
    assert not is_flaky([])

    # All pass
    assert pass_at_1([True, True]) == 1.0
    assert pass_at_k([True, True]) == 1.0
    assert pass_hat_k([True, True]) == 1.0
    assert not is_flaky([True, True])

    # All fail
    assert pass_at_1([False, False]) == 0.0
    assert pass_at_k([False, False]) == 0.0
    assert pass_hat_k([False, False]) == 0.0
    assert not is_flaky([False, False])

    # Partial / flaky
    assert pass_at_1([True, False]) == 0.5
    assert pass_at_k([True, False]) == 1.0
    assert pass_hat_k([True, False]) == 0.0
    assert is_flaky([True, False])


def test_summarize_outcomes_with_costs() -> None:
    outcomes = {
        "item-1": [
            TrialOutcome(passed=True, tokens=100, cost_usd=0.01),
            TrialOutcome(passed=True, tokens=100, cost_usd=0.01),
        ],
        "item-2": [
            TrialOutcome(passed=False, tokens=50, cost_usd=0.005),
            TrialOutcome(passed=True, tokens=50, cost_usd=0.005),
        ],
    }

    summary = summarize_outcomes(
        outcomes,
        trials=2,
        task_ids={"item-1": "task-one", "item-2": "task-two"},
    )

    assert summary.trials == 2
    assert summary.total_tasks == 2
    assert summary.total_trials == 4
    assert summary.total_successes == 3

    assert summary.pass_at_1 == 0.75  # (1.0 + 0.5) / 2
    assert summary.pass_at_k == 1.0  # (1.0 + 1.0) / 2
    assert summary.pass_hat_k == 0.5  # (1.0 + 0.0) / 2
    assert summary.flakiness_rate == 0.5  # task-two is flaky

    assert summary.mean_cost_usd is not None
    assert summary.mean_cost_usd > 0
    assert summary.success_per_dollar is not None
    assert summary.success_per_dollar > 0


def test_summarize_outcomes_tokens_only_fallback() -> None:
    outcomes = {
        "item-1": [
            TrialOutcome(passed=True, tokens=100, cost_usd=None),
        ],
    }

    summary = summarize_outcomes(outcomes, trials=1)
    assert summary.success_per_dollar is None
    assert summary.mean_cost_usd is None
    assert summary.mean_tokens == 100.0


def test_render_summary_table() -> None:
    summary = BenchmarkSummary(
        trials=1,
        per_task=[
            TaskAggregate(
                dataset_item_id="item-1",
                task_id="001-find-and-replace",
                trials=1,
                passes=1,
                pass_at_1=1.0,
                pass_at_k=1.0,
                pass_hat_k=1.0,
                is_flaky=False,
                mean_tokens=150.0,
                mean_cost_usd=None,
            )
        ],
        pass_at_1=1.0,
        pass_at_k=1.0,
        pass_hat_k=1.0,
        flakiness_rate=0.0,
        mean_tokens=150.0,
        total_successes=1,
        total_trials=1,
        total_tasks=1,
    )

    table = render_summary_table(summary)
    assert "forge benchmark" in str(table.title)


def test_attach_experiment_aggregates() -> None:
    client = MagicMock()
    mock_result = MagicMock()
    test_case = MagicMock()
    test_case.dataset_item_id = "item-1"
    test_case.trace_id = "trace-123"

    test_result = MagicMock()
    test_result.test_case = test_case
    mock_result.test_results = [test_result]

    summary = BenchmarkSummary(
        trials=1,
        per_task=[
            TaskAggregate(
                dataset_item_id="item-1",
                task_id="001-find-and-replace",
                trials=1,
                passes=1,
                pass_at_1=1.0,
                pass_at_k=1.0,
                pass_hat_k=1.0,
                is_flaky=False,
                mean_tokens=150.0,
                mean_cost_usd=0.01,
            )
        ],
    )

    attach_experiment_aggregates(client, mock_result, summary, project_name="forge-evals")
    client.log_traces_feedback_scores.assert_called_once()
    scores = client.log_traces_feedback_scores.call_args[0][0]
    names = {s["name"] for s in scores}
    assert names == {"pass_at_1", "pass_at_k", "pass_hat_k", "flaky"}
