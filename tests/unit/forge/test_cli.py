"""Unit tests for the ``forge`` CLI entrypoint.

The tests use Click's ``CliRunner`` to verify CLI invocation and argument handling.
The asynchronous ``run_app`` entrypoint is mocked so tests do not initialize the
interactive TUI or require a real terminal, Gemini API key, or model request.
"""

from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from forge.cli import cli


@pytest.fixture
def mock_run_app(mocker):
    """Prevent CLI tests from starting the interactive terminal."""
    return mocker.patch(
        "forge.cli.run_app",
        new_callable=AsyncMock,
    )


def test_cli_runs_and_exits_zero(mock_run_app):
    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with()


def test_cli_accepts_resume_flag(mock_run_app):
    result = CliRunner().invoke(cli, ["--resume"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with()


def test_cli_accepts_named_resume(mock_run_app):
    result = CliRunner().invoke(cli, ["--resume", "2026-06-19_abc"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with()
