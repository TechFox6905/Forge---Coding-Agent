"""The Opik glue that turns benchmark tasks into an ``evaluate()`` experiment (ADR-003 §3,4,5,8).

Two pieces sit on top of the sandbox lifecycle (:mod:`evals.harness.sandbox`) and the driver
(:mod:`evals.harness.driver`):

* :func:`make_benchmark_task_fn` builds the sync Opik task fn — for one dataset item it runs the real
  agent in a fresh sandbox Workspace under a BYPASS gate, grades it with the hidden oracle, and
  returns the flat payload the landed code metrics (:mod:`evals.harness.metrics`) and per-task judges
  consume: ``output`` / ``tool_calls`` / ``steps`` / token counts / a ``verify`` result / ``max_steps``
  / ``agent_error`` / ``infra_error``. The task fn NEVER raises: a crashed agent run grades as
  fail-with-reason (``agent_error``), and a sandbox that never came up grades as fail-with-reason too
  (``infra_error``), because Opik's ``evaluate`` gives task fns no per-item isolation, so one raise
  would abort the whole experiment.
* :func:`run_benchmark` loads + filters the tasks, upserts them into ``forge-benchmark-v1``, and
  calls ``opik.evaluation.evaluate`` with the code metrics + (single-task) judges,
  ``experiment_config`` carrying the agent model, provider, git sha and sandbox, and
  ``project_name=settings.eval_project_name`` so eval runs never pollute live REPL tracing.

The benchmark runs ``evaluate(task_threads=1)`` so tasks do not race on shared filesystem resources.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from evals.harness.driver import run_agent_once_sync
from evals.harness.sandbox import benchmark_sandbox
from evals.harness.task_loader import BenchmarkTask, load_benchmark_tasks
from forge.config.settings import settings

if TYPE_CHECKING:
    import opik
    from opik.evaluation.evaluation_result import EvaluationResult

    from evals.harness.driver import EvalRunRecord
    from evals.harness.task_loader import Difficulty

logger = logging.getLogger(__name__)

# The Opik task fn Opik hands one dataset item and expects one flat output dict back.
BenchmarkTaskFn = Callable[[dict[str, Any]], dict[str, Any]]


class BenchmarkSelectionError(Exception):
    """No benchmark task matched the ``--task`` / ``--difficulty`` filters — a loud, friendly stop."""


def make_benchmark_task_fn(
    tasks_by_id: dict[str, BenchmarkTask], *, sandbox: str = "local"
) -> BenchmarkTaskFn:
    """Build the sync Opik task fn that runs + grades one item's task (ADR-003 §3,4,5).

    The returned closure looks the task up by ``item["task_id"]``, runs the full sandbox lifecycle,
    and returns the metric-facing payload. Sync because Opik ``evaluate()`` task fns cannot be async.
    """

    def benchmark_task_fn(item: dict[str, Any]) -> dict[str, Any]:
        task = tasks_by_id[item["task_id"]]
        return _run_and_grade(task, sandbox=sandbox)

    return benchmark_task_fn


def _run_and_grade(task: BenchmarkTask, *, sandbox: str) -> dict[str, Any]:
    """Run + grade one task, turning ANY failure into a graded payload — never a raise (ADR-003 §3).

    Wraps the WHOLE sandbox lifecycle (creation included), retrying transient provider errors
    (429/503) with exponential backoff while failing fast on non-transient daily quota limits.
    """
    max_retries = 3
    last_payload: dict[str, Any] | None = None

    for attempt in range(max_retries):
        try:
            payload = _run_in_sandbox(task, sandbox=sandbox)
        except Exception as exc:  # a sandbox-lifecycle failure must not abort the whole experiment
            logger.exception("[eval] sandbox lifecycle failed for task %s", task.id)
            return _payload(
                None,
                verify_exit=None,
                verify_stdout="",
                verify_stderr=str(exc),
                task=task,
                agent_error=None,
                infra_error=f"sandbox lifecycle failed: {exc}",
            )

        agent_error = payload.get("agent_error")
        is_transient = agent_error and any(
            k in agent_error.lower()
            for k in (
                "429",
                "503",
                "500",
                "502",
                "504",
                "rate limit",
                "resource_exhausted",
                "quota exceeded",
                "unavailable",
                "high demand",
                "spikes in demand",
                "overloaded",
                "bad gateway",
                "gateway timeout",
                "internal server error",
            )
        )
        if is_transient and attempt < max_retries - 1:
            match = re.search(r"retry in ([\d\.]+)s", agent_error, re.IGNORECASE) or re.search(
                r"retrydelay['\":\s]+(\d+)s", agent_error, re.IGNORECASE
            )
            if match:
                delay = float(match.group(1)) + 2.0
                if delay > 120.0:
                    logger.warning(
                        "[eval] task %s hit non-transient quota limit (retry wait %.1fs > 120s); failing fast",
                        task.id,
                        delay,
                    )
                    return payload
                wait_time = delay
            elif (
                "503" in agent_error
                or "unavailable" in agent_error.lower()
                or "high demand" in agent_error.lower()
            ):
                wait_time = 10.0 * (attempt + 1)
            else:
                wait_time = 15.0 * (attempt + 1)

            logger.warning(
                "[eval] task %s hit transient provider error; waiting %.1fs before retry (%d/%d): %s",
                task.id,
                wait_time,
                attempt + 1,
                max_retries,
                agent_error[:120],
            )
            time.sleep(wait_time)
            last_payload = payload
            continue

        return payload

    return last_payload or _payload(
        None,
        verify_exit=None,
        verify_stdout="",
        verify_stderr="",
        task=task,
        agent_error="max retries exceeded",
        infra_error=None,
    )


def _run_in_sandbox(task: BenchmarkTask, *, sandbox: str) -> dict[str, Any]:
    """Bring up the Workspace, run the agent BYPASS, grade with the hidden oracle (ADR-003 §3,5).

    The agent runs BYPASS + headless deny resolvers, capped at ``max_steps`` model requests. A raised
    agent run is caught into ``agent_error`` so the oracle STILL grades the Workspace (a crash is
    fail-with-reason, not a skipped grade). A failure to even enter the sandbox, or a failure to
    grade, propagates to :func:`_run_and_grade`'s ``infra_error`` handler. The Workspace is torn down
    either way (the ``finally`` in :func:`benchmark_sandbox`).
    """
    record: EvalRunRecord | None = None
    agent_error: str | None = None
    with benchmark_sandbox(task, sandbox=sandbox) as run:
        try:
            record = run_agent_once_sync(
                task.prompt,
                cwd=run.workspace,
                gate_mode="bypass",
                max_requests=task.max_steps,
            )
            agent_error = record.agent_error
        except Exception as exc:  # a crashed agent still grades — don't skip the oracle
            logger.exception("[eval] agent run raised for task %s", task.id)
            agent_error = f"agent run raised: {exc}"
        verify = run.grade(task)
    return _payload(
        record,
        verify_exit=verify.exit_code,
        verify_stdout=verify.stdout,
        verify_stderr=verify.stderr,
        task=task,
        agent_error=agent_error,
        infra_error=None,
    )


def _payload(
    record: EvalRunRecord | None,
    *,
    verify_exit: int | None,
    verify_stdout: str,
    verify_stderr: str = "",
    task: BenchmarkTask,
    agent_error: str | None,
    infra_error: str | None,
) -> dict[str, Any]:
    """The flat output dict the landed metrics + judges read (ADR-003 §4).

    ``tool_calls`` is de-dataclassed to plain ``{"name", "args"}`` dicts so the payload is
    JSON-serializable for Opik storage; ``verify`` is the ``{"exit_code", "stdout"}`` shape
    :class:`~evals.harness.metrics.VerifyOracleMetric` maps. Two distinct failure channels, both
    absorbed by the metrics' ``**ignored_kwargs``: ``agent_error`` names a crashed agent run (the
    oracle still ran); ``infra_error`` names a sandbox that never came up or could not be graded, in
    which case ``verify.exit_code`` is ``None`` and the oracle metric grades ``0.0`` with a reason. A
    ``None`` record degrades every run field to its empty default.
    """
    tool_calls = (
        [{"name": call.name, "args": call.args} for call in record.tool_calls] if record else []
    )
    return {
        "output": record.output if record else "",
        "tool_calls": tool_calls,
        "steps": record.steps if record else 0,
        "input_tokens": record.input_tokens if record else 0,
        "output_tokens": record.output_tokens if record else 0,
        "verify": {
            "exit_code": verify_exit,
            "stdout": verify_stdout,
            "stderr": verify_stderr,
        },
        "max_steps": task.max_steps,
        "agent_error": agent_error,
        "infra_error": infra_error,
    }


def run_benchmark(
    *,
    task_id: str | None = None,
    difficulty: Difficulty | None = None,
    sandbox: str = "local",
    nb_samples: int | None = None,
    trials: int = 1,
    client: opik.Opik | None = None,
) -> EvaluationResult:
    """Run the filtered benchmark as one Opik experiment and return its result (ADR-003 §3,4,5,8).

    Loads every task, applies the ``--task`` / ``--difficulty`` filters, upserts the selection into
    ``forge-benchmark-v1``, and calls ``evaluate`` scoped (via ``dataset_item_ids``) to just those
    items with the code metrics + single-task judges. ``trials`` rides Opik's own ``trial_count`` axis
    (``k`` runs per item); after the run, the trial aggregates (pass@1/pass@k/pass^k/flakiness + cost,
    :mod:`evals.harness.aggregates`) are attached to the experiment as trace feedback scores.
    ``experiment_config`` records the agent model, provider, git sha and sandbox; ``project_name`` is
    ``settings.eval_project_name`` so live tracing stays clean. Runs single-threaded. Raises
    :class:`BenchmarkSelectionError` when nothing matches.
    """
    import opik
    from opik.evaluation import evaluate

    from evals.harness.datasets import sync_benchmark_dataset

    if trials < 1:
        raise ValueError(f"trials must be >= 1, got {trials}.")

    all_tasks = load_benchmark_tasks()
    selected = _select_tasks(all_tasks, task_id=task_id, difficulty=difficulty)
    if not selected:
        raise BenchmarkSelectionError(
            f"no benchmark task matched (task={task_id!r}, difficulty={difficulty!r}); "
            f"{len(all_tasks)} task(s) available."
        )

    client = client or opik.Opik()
    dataset = sync_benchmark_dataset(selected, client=client)
    item_ids = _selected_item_ids(dataset, {task.id for task in selected})

    tasks_by_id = {task.id: task for task in all_tasks}
    task_fn = make_benchmark_task_fn(tasks_by_id, sandbox=sandbox)
    result = evaluate(
        dataset=dataset,
        task=task_fn,
        scoring_metrics=_scoring_metrics(selected),
        experiment_config=experiment_config(sandbox),
        project_name=settings.eval_project_name,
        nb_samples=nb_samples,
        dataset_item_ids=item_ids or None,
        task_threads=1,
        trial_count=trials,
    )
    _attach_aggregates(client, result, trials)
    return result


def _attach_aggregates(client: opik.Opik, result: EvaluationResult, trials: int) -> None:
    """Log the post-hoc trial aggregates onto the experiment's traces — best-effort (ADR-003 §8)."""
    from evals.harness.aggregates import attach_experiment_aggregates, summarize

    try:
        summary = summarize(result, trials=trials)
        attach_experiment_aggregates(
            client, result, summary, project_name=settings.eval_project_name
        )
    except Exception:  # a completed run must not fail on its post-hoc bookkeeping
        logger.exception("[eval] failed to attach trial aggregates to the experiment")


def _select_tasks(
    tasks: list[BenchmarkTask], *, task_id: str | None, difficulty: Difficulty | None
) -> list[BenchmarkTask]:
    """Filter loaded tasks by exact ``task_id`` and/or ``difficulty`` (both optional, AND-combined)."""
    selected = tasks
    if task_id is not None:
        selected = [task for task in selected if task.id == task_id]
    if difficulty is not None:
        selected = [task for task in selected if task.difficulty == difficulty]
    return selected


def _selected_item_ids(dataset: Any, selected_ids: set[str]) -> list[str]:
    """The dataset item ids whose ``task_id`` is in ``selected_ids`` — scopes ``evaluate`` to the run."""
    items = dataset.get_items()
    return [
        item["id"]
        for item in items
        if item.get("task_id") in selected_ids and item.get("id") is not None
    ]


def _scoring_metrics(tasks: list[BenchmarkTask]) -> list[Any]:
    """The metric list for the run: the code oracles always, plus a single task's G-Eval judges."""
    from evals.harness.judges import make_judge
    from evals.harness.metrics import MaxStepsMetric, VerifyOracleMetric

    metrics: list[Any] = [VerifyOracleMetric(), MaxStepsMetric()]
    if len(tasks) == 1:
        metrics += [
            make_judge(spec.task_introduction, spec.evaluation_criteria) for spec in tasks[0].judges
        ]
    return metrics


def experiment_config(sandbox: str = "local") -> dict[str, Any]:
    """The Opik ``experiment_config`` for a run: the agent model, provider, git sha and sandbox."""
    return {
        "agent_model": agent_model(),
        "provider": "gemini",
        "git_sha": git_sha(),
        "sandbox": sandbox,
    }


def agent_model() -> str:
    """The model string the agent runs on, resolved from settings."""
    return settings.gemini_model


def git_sha() -> str:
    """The current commit sha, or ``"unknown"`` if git is unavailable."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"
