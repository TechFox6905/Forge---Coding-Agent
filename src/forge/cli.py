"""The ``forge`` CLI entrypoint.

Thin by design: it bootstraps logging, then (from task 002 onward) hands off to the
TUI + harness. ``init_logger()`` runs at module level before any other project import.
"""

from __future__ import annotations

from forge.logging import init_logger

init_logger()

import asyncio  # noqa: E402  (intentional post-logger import)
import logging  # noqa: E402

import click  # noqa: E402

from forge.tui.app import run_app  # noqa: E402

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--resume",
    is_flag=False,
    flag_value="latest",
    default=None,
    metavar="[SESSION]",
    help="Resume the latest session, or a named session id. (Wired in task 014.)",
)
def cli(resume: str | None) -> None:
    """forge — a terminal coding agent you run in your terminal."""
    logger.debug("forge starting (resume=%s)", resume)
    # Task 002: launch the echo REPL. The agent loop is wired in tasks 003+.
    asyncio.run(run_app())


if __name__ == "__main__":
    cli()
