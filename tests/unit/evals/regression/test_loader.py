"""Unit tests for evals.regression.loader (ADR-003 §6; Task 024)."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.regression.loader import (
    RegressionProbeError,
    load_probes,
    probe_by_id,
)
from evals.regression.probe import RegressionProbe


def test_load_all_probes() -> None:
    """All declared regression probes must load with unique IDs and valid definitions."""
    probes = load_probes()
    assert len(probes) >= 15, "At least 15 regression probes must be defined"

    ids = [p.id for p in probes]
    assert len(set(ids)) == len(ids), "Every probe ID must be unique"

    for probe in probes:
        assert isinstance(probe, RegressionProbe)
        assert probe.id.strip()
        assert probe.prompt.strip()
        assert len(probe.metrics) > 0


def test_probe_by_id_found() -> None:
    probes = load_probes()
    first = probes[0]
    found = probe_by_id(first.id, probes)
    assert found == first


def test_probe_by_id_missing() -> None:
    with pytest.raises(RegressionProbeError, match="no regression probe with id"):
        probe_by_id("non-existent-probe-id-99999")


def test_load_probes_missing_dir(tmp_path: Path) -> None:
    assert load_probes(tmp_path / "empty") == []


def test_reject_duplicate_ids() -> None:
    from evals.harness.metrics import MaxStepsMetric
    from evals.regression.loader import _reject_duplicate_ids

    probe1 = RegressionProbe("dup", "p1", lambda w: None, [MaxStepsMetric()])
    probe2 = RegressionProbe("dup", "p2", lambda w: None, [MaxStepsMetric()])

    with pytest.raises(RegressionProbeError, match="duplicate regression probe id"):
        _reject_duplicate_ids([probe1, probe2])
