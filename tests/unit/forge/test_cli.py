"""Unit tests for the `forge` CLI entrypoint.

The tests use `CliRunner` to invoke the CLI and mock `forge.cli.run_app` so they
do not start the interactive terminal or make model requests. They verify that
the CLI exits successfully and forwards the expected `resume` argument to
`run_app`.
"""

from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner
from pydantic import SecretStr

from forge import cli as cli_mod
from forge.cli import cli


@pytest.fixture
def mock_run_app(mocker):
    """Prevent CLI tests from starting the interactive terminal."""
    return mocker.patch(
        "forge.cli.run_app",
        new_callable=AsyncMock,
    )


def test_cli_runs_and_exits_zero(mock_run_app, mocker):
    mocker.patch.object(
        cli_mod.settings,
        "gemini_api_key",
        SecretStr("test-api-key"),
    )
    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with(resume=None)


def test_cli_accepts_resume_flag(mock_run_app, mocker):
    mocker.patch.object(
        cli_mod.settings,
        "gemini_api_key",
        SecretStr("test-api-key"),
    )
    result = CliRunner().invoke(cli, ["--resume"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with(resume="latest")


def test_cli_accepts_named_resume(mock_run_app, mocker):
    mocker.patch.object(
        cli_mod.settings,
        "gemini_api_key",
        SecretStr("test-api-key"),
    )
    result = CliRunner().invoke(cli, ["--resume", "2026-06-19_abc"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once_with(resume="2026-06-19_abc")


def test_cli_passes_no_resume_by_default(mocker):
    mocker.patch.object(
        cli_mod.settings,
        "gemini_api_key",
        SecretStr("test-api-key"),
    )
    # Without --resume the CLI starts a fresh session (run_app gets resume=None).
    run_app = mocker.patch("forge.cli.run_app", new=AsyncMock())

    CliRunner().invoke(cli, [])

    run_app.assert_awaited_once()
    assert run_app.await_args.kwargs.get("resume") is None


def test_cli_passes_latest_resume_for_the_bare_flag(mocker):
    mocker.patch.object(
        cli_mod.settings,
        "gemini_api_key",
        SecretStr("test-api-key"),
    )
    # `--resume` with no value resumes the latest session (run_app gets resume="latest").
    run_app = mocker.patch("forge.cli.run_app", new=AsyncMock())

    CliRunner().invoke(cli, ["--resume"])

    run_app.assert_awaited_once()
    assert run_app.await_args.kwargs.get("resume") == "latest"


def test_cli_passes_named_resume_through(mocker):
    mocker.patch.object(
        cli_mod.settings,
        "gemini_api_key",
        SecretStr("test-api-key"),
    )
    # `--resume <id>` resumes that named session (run_app gets resume=<id>).
    run_app = mocker.patch("forge.cli.run_app", new=AsyncMock())

    CliRunner().invoke(cli, ["--resume", "2026-06-19_abc"])

    run_app.assert_awaited_once()
    assert run_app.await_args.kwargs.get("resume") == "2026-06-19_abc"


# --- task 004 carryover: the no-key startup guard (friendly line, no traceback) -------------


def test_cli_with_no_gemini_key_exits_nonzero_with_a_friendly_line(mocker):
    """No ``GEMINI_API_KEY`` → one friendly line on stderr, non-zero exit, NO traceback.

    Without the guard, ``build_agent()`` raises a raw ``pydantic_ai.UserError`` from
    ``GoogleProvider`` (mentioning ``GOOGLE_API_KEY`` — the wrong var for this project), which
    surfaces as an ugly traceback. The guard checks ``settings.gemini_api_key`` *before* building
    the agent and exits cleanly instead.
    """
    mocker.patch.object(cli_mod.settings, "gemini_api_key", SecretStr(""))
    # run_app must never be reached — the guard fires first, so a stub proves it is not called.
    run_app = mocker.patch("forge.cli.run_app", new=mocker.AsyncMock())

    result = CliRunner().invoke(cli, [])

    assert result.exit_code != 0
    # A friendly one-liner naming the fix, not a traceback.
    assert "GEMINI_API_KEY" in result.output
    assert ".env.example" in result.output
    assert "Traceback" not in result.output
    # The guard short-circuited before the REPL / agent build.
    run_app.assert_not_awaited()


def test_cli_with_a_present_gemini_key_does_not_trip_the_guard(mocker):
    """A present key does NOT trigger the guard: the CLI proceeds to ``run_app`` normally."""
    mocker.patch.object(cli_mod.settings, "gemini_api_key", SecretStr("a-real-looking-key"))
    run_app = mocker.patch("forge.cli.run_app", new=mocker.AsyncMock())

    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    run_app.assert_awaited_once()
