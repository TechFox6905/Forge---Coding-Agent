"""Probe 15 — a seeded ``AGENTS.md`` naming rule is obeyed (ADR-001 §8; ADR-003 §2,6).

Memory-obedience discipline: a project ``AGENTS.md`` is injected into the agent's system
prompt every turn, so a rule it states must actually steer behavior. The fixture seeds an ``AGENTS.md``
carrying ONE unambiguous naming rule — every new Python file's name must start with ``fg_`` — and the
prompt asks the agent to create a new Python module. The run passes when the agent created at least one
``.py`` file AND every ``.py`` file it created obeys the ``fg_`` prefix (:class:`NewFileNameMetric`, a
mechanical filename check — no judge needed).
"""

from __future__ import annotations

from pathlib import Path

from evals.harness.metrics import MaxStepsMetric, NewFileNameMetric
from evals.regression.probe import RegressionProbe

# The unambiguous naming rule the seeded AGENTS.md states and the metric enforces.
REQUIRED_PREFIX = "fg_"

_AGENTS_MD = (
    "# Project conventions\n\n"
    "## File naming\n\n"
    f"Every new Python file you create MUST have a filename that starts with `{REQUIRED_PREFIX}`. "
    "This is a hard rule — never create a `.py` file whose name does not start with "
    f"`{REQUIRED_PREFIX}`.\n"
)


def _obeys_prefix(basename: str) -> bool:
    """Whether a created Python file's basename obeys the seeded ``fg_`` naming rule."""
    return basename.startswith(REQUIRED_PREFIX)


def _fixture(workspace: Path) -> None:
    """Seed the ``AGENTS.md`` naming rule the memory loader injects into the system prompt."""
    (workspace / "AGENTS.md").write_text(_AGENTS_MD, encoding="utf-8")


PROBE = RegressionProbe(
    id="15-memory-obedience",
    prompt=(
        "Create a new Python module with a helper function that reverses a string. Choose the filename "
        "yourself and follow this project's conventions."
    ),
    fixture=_fixture,
    metrics=[
        NewFileNameMetric(
            ".py",
            _obeys_prefix,
            description=f"every new .py filename starts with {REQUIRED_PREFIX!r}",
            name="new_py_files_prefixed_fg",
        ),
        MaxStepsMetric(),
    ],
    max_requests=5,
    tags=["memory-obedience", "instruction-following"],
)
