"""Unit tests for the `forge` CLI entrypoint.

The tests use `CliRunner` to invoke the CLI and mock `forge.cli.run_app` so they
do not start the interactive terminal or make model requests. They verify that
the CLI exits successfully and forwards the expected `resume` argument to
`run_app`.
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
    mock_run_app.assert_awaited_once_with(resume=None)


def test_cli_accepts_resume_flag(mock_run_app):
    result = CliRunner().invoke(cli, ["--resume"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with(resume="latest")


def test_cli_accepts_named_resume(mock_run_app):
    result = CliRunner().invoke(cli, ["--resume", "2026-06-19_abc"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with(resume="2026-06-19_abc")


def test_cli_passes_no_resume_by_default(mocker):
    # Without --resume the CLI starts a fresh session (run_app gets resume=None).
    run_app = mocker.patch("forge.cli.run_app", new=AsyncMock())

    CliRunner().invoke(cli, [])

    run_app.assert_awaited_once()
    assert run_app.await_args.kwargs.get("resume") is None


def test_cli_passes_latest_resume_for_the_bare_flag(mocker):
    # `--resume` with no value resumes the latest session (run_app gets resume="latest").
    run_app = mocker.patch("forge.cli.run_app", new=AsyncMock())

    CliRunner().invoke(cli, ["--resume"])

    run_app.assert_awaited_once()
    assert run_app.await_args.kwargs.get("resume") == "latest"


def test_cli_passes_named_resume_through(mocker):
    # `--resume <id>` resumes that named session (run_app gets resume=<id>).
    run_app = mocker.patch("forge.cli.run_app", new=AsyncMock())

    CliRunner().invoke(cli, ["--resume", "2026-06-19_abc"])

    run_app.assert_awaited_once()
    assert run_app.await_args.kwargs.get("resume") == "2026-06-19_abc"
