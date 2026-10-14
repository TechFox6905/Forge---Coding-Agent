from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from forge.cli import cli


def test_cli_runs_and_exits_zero():
    with patch("forge.cli.run_app", new_callable=AsyncMock) as mock_run_app:
        result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once()


def test_cli_accepts_resume_flag():
    with patch("forge.cli.run_app", new_callable=AsyncMock) as mock_run_app:
        result = CliRunner().invoke(cli, ["--resume"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once()


def test_cli_accepts_named_resume():
    with patch("forge.cli.run_app", new_callable=AsyncMock) as mock_run_app:
        result = CliRunner().invoke(cli, ["--resume", "2026-06-19_abc"])

    assert result.exit_code == 0
    mock_run_app.assert_awaited_once()
