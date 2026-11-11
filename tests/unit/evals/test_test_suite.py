"""Unit tests for evals.harness.test_suite (ADR-003 §6; Task 025)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evals.harness.metrics import MaxStepsMetric
from evals.harness.test_suite import (
    SUITE_PASS_BAR,
    SuitePassRateError,
    SuiteUnavailableError,
    assert_pass_rate,
    build_suite,
    make_suite_task_fn,
    run_test_suite,
    select_suite_probes,
    suite_api_available,
    suite_items,
)
from evals.regression.probe import RegressionProbe


def test_select_suite_probes() -> None:
    probes = [
        RegressionProbe("dummy-1", "p1", lambda w: None, [MaxStepsMetric()]),
        RegressionProbe("17-grounded-answer", "p2", lambda w: None, [MaxStepsMetric()]),
        RegressionProbe("18-no-hallucinated-files", "p3", lambda w: None, [MaxStepsMetric()]),
    ]

    selected = select_suite_probes(probes)
    selected_ids = [p.id for p in selected]
    assert selected_ids == ["17-grounded-answer", "18-no-hallucinated-files"]


def test_suite_items_structure() -> None:
    probe = RegressionProbe("17-grounded-answer", "prompt text", lambda w: None, [MaxStepsMetric()])
    items = suite_items([probe])

    assert len(items) == 1
    assert items[0]["data"] == {"probe_id": "17-grounded-answer"}
    assert "assertions" in items[0]
    assert len(items[0]["assertions"]) > 0


def test_make_suite_task_fn() -> None:
    probe = RegressionProbe("01-probe", "Test prompt", lambda w: None, [MaxStepsMetric()])
    probes_by_id = {"01-probe": probe}

    with patch("evals.harness.test_suite.make_regression_task_fn") as mock_make_reg:
        mock_reg_fn = MagicMock(return_value={"output": "agent answer"})
        mock_make_reg.return_value = mock_reg_fn

        suite_task = make_suite_task_fn(probes_by_id)
        result = suite_task({"probe_id": "01-probe"})

    assert result == {
        "input": {"prompt": "Test prompt"},
        "output": "agent answer",
    }


def test_build_suite() -> None:
    client = MagicMock()
    mock_suite = MagicMock()
    client.get_or_create_test_suite.return_value = mock_suite

    probe = RegressionProbe("17-grounded-answer", "p", lambda w: None, [MaxStepsMetric()])
    suite = build_suite(client, [probe])

    assert suite == mock_suite
    client.get_or_create_test_suite.assert_called_once()
    mock_suite.insert.assert_called_once()


def test_assert_pass_rate() -> None:
    # Above or at bar passes cleanly
    assert_pass_rate(SUITE_PASS_BAR)
    assert_pass_rate(1.0)

    # Below bar raises SuitePassRateError
    with pytest.raises(SuitePassRateError, match="below the bar"):
        assert_pass_rate(SUITE_PASS_BAR - 0.1)


def test_suite_api_available_checks() -> None:
    client_without_api = MagicMock(spec=[])
    assert not suite_api_available(client_without_api)

    client_with_api = MagicMock()
    client_with_api.get_or_create_test_suite = MagicMock()
    with patch("opik.run_tests", create=True):
        assert suite_api_available(client_with_api)


def test_run_test_suite_unavailable_raises() -> None:
    client = MagicMock(spec=[])
    with pytest.raises(SuiteUnavailableError, match=r"Opik Test Suites need opik>=2\.0"):
        run_test_suite(client=client)
