"""Fail-fast key preflight for ``make eval-benchmark`` / ``make eval-regression`` (ADR-003 §9).

Both targets drive the REAL agent (GEMINI_API_KEY), store the experiment in Opik (``OPIK_API_KEY``),
and run judges on Groq (``GROQ_API_KEY``).
Without them the underlying command tracebacks deep in opik/inference. This module is the guard the
Makefile runs FIRST — invoked as ``python -m evals.harness.keys``:

* it reads the resolved forge ``settings`` (imported lazily), so a key set in ``.env`` counts, not just
  the process env;
* when a required key is missing it prints ONE friendly line and exits non-zero, so the Make recipe
  skips the expensive command instead of crashing.
"""

from __future__ import annotations

import os

import click


def eval_keys_missing() -> list[str]:
    """The env-var names an eval target needs but does not have — empty means good to run (ADR-003 §9).

    The single shared, settings-backed key preflight for the whole suite.
    ``OPIK_API_KEY``, ``GEMINI_API_KEY``, and ``GROQ_API_KEY`` are all checked.
    """
    from forge.config.settings import settings

    missing: list[str] = []
    if (
        not settings.opik_api_key.get_secret_value().strip()
        and not os.environ.get("OPIK_API_KEY", "").strip()
    ):
        missing.append("OPIK_API_KEY")
    if (
        not settings.gemini_api_key.get_secret_value().strip()
        and not os.environ.get("GEMINI_API_KEY", "").strip()
    ):
        missing.append("GEMINI_API_KEY")
    if (
        not settings.groq_api_key.get_secret_value().strip()
        and not os.environ.get("GROQ_API_KEY", "").strip()
    ):
        missing.append("GROQ_API_KEY")
    return missing


def main() -> int:
    """Exit 0 when every required key resolves; else print one friendly skip line and exit 1."""
    missing = eval_keys_missing()
    if missing:
        click.echo(
            "evals: skipped — set "
            + ", ".join(missing)
            + " to run (see the Evaluation suite block in .env.example).",
            err=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    from forge.logging import init_logger

    init_logger()

    raise SystemExit(main())
