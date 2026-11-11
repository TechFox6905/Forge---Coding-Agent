"""Per-task-run sandbox lifecycle, reusing Forge's command executor seam (ADR-003 §3,5).

A benchmark run needs a fresh, isolated Workspace per task and a hidden oracle that the agent can
never see during its run. Both are handled through Forge's existing execution architecture:
a temporary Workspace directory on the host and :class:`~forge.tools.exec.LocalExecutor`.

:func:`benchmark_sandbox` is a sync context manager (Opik task fns are sync) that, for one task run:

1. seeds ``setup/`` into a fresh temp Workspace;
2. runs ``setup/setup.sh`` inside the workspace via the executor if present;
3. yields a :class:`SandboxRun` the caller drives the agent against and then GRADES — verify assets
   are injected into the Workspace only at :meth:`SandboxRun.grade` time, so ``verify.sh`` never exists
   in the Workspace while the agent runs (ADR-003 §5);
4. tears down and removes the temp Workspace in a ``finally`` — on success AND on any
   agent / verify failure.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evals.harness.task_loader import VERIFY_SCRIPT_NAME, BenchmarkTask
from forge.tools.exec import CommandExecutor, ExecResult, LocalExecutor

logger = logging.getLogger(__name__)

# The optional post-seed setup entrypoint a task may ship (git history, a sqlite DB, mixed encodings).
SETUP_SCRIPT_NAME = "setup.sh"

# Wall-clock cap for a harness-run helper command (setup.sh / verify.sh) inside the workspace.
HELPER_TIMEOUT_S = 300.0


@dataclass(frozen=True, slots=True)
class SandboxRun:
    """A live per-task Workspace behind the executor seam (ADR-003 §3,5).

    ``workspace`` is the fresh temp Workspace root the agent's tools are pointed at; ``executor`` is
    the :class:`~forge.tools.exec.CommandExecutor` commands ride. Callers run the
    agent, then call :meth:`grade` — nothing injects ``verify/`` before that, so the oracle is hidden
    for the whole run.
    """

    workspace: Path
    executor: CommandExecutor = field(default_factory=LocalExecutor)

    def run(self, command: str, *, timeout_s: float = HELPER_TIMEOUT_S) -> ExecResult:
        """Run one command inside the Workspace through the executor (sync; wraps the async exec)."""
        return _run_async(self.executor.run(command, cwd=self.workspace, timeout_s=timeout_s))

    def grade(self, task: BenchmarkTask) -> ExecResult:
        """Inject the hidden ``verify/`` assets into the Workspace, then run ``bash verify.sh`` (ADR-003 §5).

        Called only after the agent finishes, so the oracle never existed in the Workspace during the run.
        """
        self._inject(task.verify_script.parent)
        return self.run(f"bash {VERIFY_SCRIPT_NAME}")

    def _inject(self, source_dir: Path) -> None:
        """Write every file under ``source_dir`` into the Workspace root."""
        if not source_dir.is_dir():
            return
        shutil.copytree(source_dir, self.workspace, dirs_exist_ok=True)


@contextmanager
def benchmark_sandbox(task: BenchmarkTask, *, sandbox: str = "local") -> Iterator[SandboxRun]:
    """Bring up an isolated per-run Workspace for ``task`` and tear it down afterwards (ADR-003 §3,5).

    The Workspace is a fresh temp dir seeded with ``setup/``; ``setup/setup.sh`` runs after create.
    The ``finally`` deletes the temp Workspace whether the ``with`` body succeeds or raises.
    """
    workspace = Path(tempfile.mkdtemp(prefix="forge-eval-")).resolve()
    executor = LocalExecutor()
    try:
        _seed_setup(task, workspace)
        _run_setup_script(executor, workspace, task)
        yield SandboxRun(workspace=workspace, executor=executor)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _seed_setup(task: BenchmarkTask, workspace: Path) -> None:
    """Copy ``setup/`` verbatim into the fresh Workspace before running (host-side)."""
    if task.setup_dir.is_dir():
        shutil.copytree(task.setup_dir, workspace, dirs_exist_ok=True)


def _run_setup_script(executor: CommandExecutor, workspace: Path, task: BenchmarkTask) -> None:
    """Run ``setup/setup.sh`` inside the workspace, if the task ships one.

    A non-zero exit is logged, not raised: the benchmark still grades the resulting Workspace (a broken
    setup grades as a task failure), and the harness never crashes on one bad task.
    """
    if not (workspace / SETUP_SCRIPT_NAME).is_file():
        return
    result = _run_async(
        executor.run(f"bash {SETUP_SCRIPT_NAME}", cwd=workspace, timeout_s=HELPER_TIMEOUT_S)
    )
    if result.exit_code != 0:
        raise RuntimeError(
            f"setup.sh failed for {task.id} (exit {result.exit_code}): {result.stderr.strip()}"
        )


def _run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run one coroutine to completion on a fresh loop.

    The benchmark task fn is sync (Opik requires it) and holds no loop-bound handle across calls (each
    command spawns a fresh subprocess), so a per-call :func:`asyncio.run` is correct.
    """
    return asyncio.run(coro)
