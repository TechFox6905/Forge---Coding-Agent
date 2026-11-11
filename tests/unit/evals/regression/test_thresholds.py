"""Unit tests for evals.regression.thresholds (ADR-003 §6; Task 025)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from evals.regression.thresholds import (
    JUDGE_METRIC_NAME,
    JUDGE_METRIC_THRESHOLD,
    TOOL_DISCIPLINE_THRESHOLD,
    BaselineCandidate,
    baseline_scores_from_feedback,
    compare_to_baseline,
    evaluate_thresholds,
    format_deltas,
    format_failures,
    latest_baseline,
    scores_from_aggregation,
    threshold_for,
)


@dataclass
class DummyStat:
    mean: float


@dataclass
class DummyFeedback:
    name: str
    value: float


def test_threshold_for() -> None:
    assert threshold_for("tool_called_read") == TOOL_DISCIPLINE_THRESHOLD
    assert threshold_for(JUDGE_METRIC_NAME) == JUDGE_METRIC_THRESHOLD


def test_evaluate_thresholds_all_pass() -> None:
    scores = {
        "tool_called_read": 1.0,
        JUDGE_METRIC_NAME: 0.85,
    }
    report = evaluate_thresholds(scores)
    assert not report.empty
    assert report.passed
    assert len(report.failures) == 0
    assert "all metrics cleared" in format_failures(report)


def test_evaluate_thresholds_with_failure() -> None:
    scores = {
        "tool_called_read": 0.5,  # below 0.8
        JUDGE_METRIC_NAME: 0.85,
    }
    report = evaluate_thresholds(scores)
    assert not report.empty
    assert not report.passed
    assert len(report.failures) == 1
    assert report.failures[0].name == "tool_called_read"
    msg = format_failures(report)
    assert "tool_called_read" in msg
    assert "NOT met" in msg


def test_evaluate_thresholds_empty() -> None:
    report = evaluate_thresholds({})
    assert report.empty
    assert report.passed


def test_compare_to_baseline() -> None:
    current = {"metric_a": 0.9, "metric_b": 0.6, "new_metric": 1.0}
    baseline = {"metric_a": 0.85, "metric_b": 0.8}

    deltas = compare_to_baseline(current, baseline, tolerance=0.05)
    assert len(deltas) == 2

    delta_map = {d.name: d for d in deltas}
    assert delta_map["metric_a"].delta > 0
    assert not delta_map["metric_a"].regressed

    assert delta_map["metric_b"].delta < -0.05
    assert delta_map["metric_b"].regressed

    table = format_deltas(deltas)
    assert "REGRESSED" in table
    assert "metric_b" in table


def test_latest_baseline() -> None:
    t1 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    c_empty = BaselineCandidate("exp-0", t1, {})
    c1 = BaselineCandidate("exp-1", t1, {"metric": 0.8})
    c2 = BaselineCandidate("exp-2", t2, {"metric": 0.9})

    assert latest_baseline([]) is None
    assert latest_baseline([c_empty]) is None
    assert latest_baseline([c1, c2]) == c2
    assert latest_baseline([c2, c1]) == c2


def test_scores_from_aggregation_and_feedback() -> None:
    agg = {"metric_x": DummyStat(mean=0.95)}
    scores = scores_from_aggregation(agg)
    assert scores == {"metric_x": 0.95}

    fb = [DummyFeedback("metric_y", 0.77)]
    fb_scores = baseline_scores_from_feedback(fb)
    assert fb_scores == {"metric_y": 0.77}
