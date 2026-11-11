"""Unit tests for evals.regression.probe (ADR-003 §6; Task 024)."""

from __future__ import annotations

import pytest

from evals.harness.metrics import MaxStepsMetric
from evals.regression.probe import RegressionProbe


def test_probe_valid_creation() -> None:
    probe = RegressionProbe(
        id="test-probe",
        prompt="Do something",
        fixture=lambda w: None,
        metrics=[MaxStepsMetric()],
        gate_mode="bypass",
        tags=["unit"],
    )
    assert probe.id == "test-probe"
    assert probe.prompt == "Do something"
    assert probe.gate_mode == "bypass"
    assert probe.tags == ["unit"]
    assert probe.skip_reason is None


def test_probe_rejects_blank_id() -> None:
    with pytest.raises(ValueError, match="id must not be blank"):
        RegressionProbe(
            id="   ",
            prompt="Do something",
            fixture=lambda w: None,
            metrics=[MaxStepsMetric()],
        )


def test_probe_rejects_blank_prompt() -> None:
    with pytest.raises(ValueError, match="prompt must not be blank"):
        RegressionProbe(
            id="test-probe",
            prompt="   ",
            fixture=lambda w: None,
            metrics=[MaxStepsMetric()],
        )


def test_probe_rejects_empty_metrics() -> None:
    with pytest.raises(ValueError, match="at least one metric is required"):
        RegressionProbe(
            id="test-probe",
            prompt="Do something",
            fixture=lambda w: None,
            metrics=[],
        )
