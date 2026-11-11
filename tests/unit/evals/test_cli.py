"""Unit tests for the ``evals`` CLI (ADR-003 §1; task 020).

Asserts CLI help, command registration, and error handling without requiring Opik or network.
"""

from __future__ import annotations

import click
from click.testing import CliRunner

from evals.run import _opik_error_as_click, cli


def test_cli_help() -> None:
    """``python -m evals --help`` prints usage and lists subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "benchmark" in result.output
    assert "regression" in result.output
    assert "suite" in result.output
    assert "online" in result.output
    assert "sync" in result.output


def test_benchmark_subcommand_help() -> None:
    """``benchmark --help`` documents its options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "--task" in result.output
    assert "--difficulty" in result.output
    assert "--trials" in result.output


def test_regression_subcommand_help() -> None:
    """``regression --help`` documents its options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["regression", "--help"])
    assert result.exit_code == 0
    assert "--probe" in result.output


def test_online_subcommand_help() -> None:
    """``online --help`` documents its options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["online", "--help"])
    assert result.exit_code == 0
    assert "--filter" in result.output


def test_suite_subcommand_help() -> None:
    """``suite --help`` succeeds without arguments."""
    runner = CliRunner()
    result = runner.invoke(cli, ["suite", "--help"])
    assert result.exit_code == 0


def test_sync_subcommand_help() -> None:
    """``sync --help`` documents its options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--benchmark" in result.output
    assert "--regression" in result.output


def test_opik_error_as_click_formatting() -> None:
    """Test Opik error translation to user-friendly ClickException."""

    class DummyAuthError(Exception):
        status_code = 401

    class DummyNetworkError(Exception):
        status_code = 500

    auth_click = _opik_error_as_click(DummyAuthError())
    assert isinstance(auth_click, click.ClickException)
    assert "rejected the API key" in auth_click.message

    net_click = _opik_error_as_click(DummyNetworkError())
    assert "Opik request failed (500)" in net_click.message
