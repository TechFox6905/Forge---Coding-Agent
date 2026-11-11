"""The Opik glue that runs the behavior probes host-native and scores them (ADR-003 §3,4,6).

Two pieces sit on top of the eval driver (:mod:`evals.harness.driver`) and the probe registry
(:mod:`evals.regression.loader`):

* :func:`make_regression_task_fn` builds the sync Opik task fn. For one dataset item it builds the
  probe's fixture in a fresh ``tempfile`` dir, runs the REAL agent HOST-NATIVE under the probe's
  gate policy / resolvers / pre-filled history / request cap, snapshots the resulting file tree,
  and returns the flat payload the code metrics + judges read. The task fn NEVER raises: a crashed
  agent run grades as fail-with-reason (``agent_error``) and a fixture / setup failure grades as
  fail-with-reason (``infra_error``), because Opik's ``evaluate`` gives task fns no per-item
  isolation — one raise would abort the whole experiment. The temp dir is always removed.
* :func:`run_regression` loads + filters the probes, upserts them into ``forge-regression-v1``, and
  calls ``opik.evaluation.evaluate`` scoped to the selected items with the probe-scoped metrics,
  ``experiment_config`` carrying the agent model + provider + git sha, and
  ``project_name=settings.eval_project_name`` so eval runs never pollute live REPL tracing.

Per-probe metric binding: ``evaluate`` applies ONE metric list to EVERY item, but each probe declares
its OWN metrics. :class:`ProbeScopedMetric` wraps every probe's metric so it scores only the item whose
``probe_id`` matches and returns ``[]`` (zero scores) for every other item — so a single ``evaluate``
call returns one :class:`~opik.evaluation.evaluation_result.EvaluationResult` with clean per-probe scores,
no cross-probe noise.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from opik.evaluation.metrics.base_metric import BaseMetric

from evals.harness.driver import run_agent_once_sync
from evals.regression.loader import load_probes
from evals.regression.probe import RegressionProbe
from forge.config.settings import settings

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    import opik
    from opik.evaluation.evaluation_result import EvaluationResult
    from opik.evaluation.metrics.score_result import ScoreResult

    from evals.harness.driver import EvalRunRecord

logger = logging.getLogger(__name__)

# The Opik task fn Opik hands one dataset item and expects one flat output dict back.
RegressionTaskFn = Callable[[dict[str, Any]], dict[str, Any]]

# Cap the per-file snapshot so a probe that writes a huge file can't bloat the Opik payload; a file
# over this size is recorded as an elision marker instead of its bytes.
_MAX_SNAPSHOT_BYTES = 64 * 1024


class RegressionSelectionError(Exception):
    """No regression probe matched the ``--probe`` filter — a loud, friendly stop."""


class ProbeScopedMetric(BaseMetric):
    """Bind ``inner`` to one probe: score only that probe's item, contribute nothing to others.

    ``evaluate`` runs every metric against every item; a probe's metric is only meaningful on its own
    item. This wrapper reads the item's ``probe_id`` and delegates to ``inner`` only on a match, else
    returns ``[]`` — Opik treats an empty list as zero score results, so the metric simply does not
    apply to that item. ``track=False`` for the same offline reason the code metrics use (ADR-003 §9).
    """

    def __init__(self, probe_id: str, inner: BaseMetric) -> None:
        super().__init__(name=inner.name, track=False)
        self._probe_id = probe_id
        self._inner = inner

    def score(self, probe_id: Any = None, **kwargs: Any) -> ScoreResult | list[ScoreResult]:
        if probe_id != self._probe_id:
            return []
        return self._inner.score(probe_id=probe_id, **kwargs)


def make_regression_task_fn(probes_by_id: dict[str, RegressionProbe]) -> RegressionTaskFn:
    """Build the sync Opik task fn that runs + grades one probe item (ADR-003 §4,6).

    The returned closure looks the probe up by ``item["probe_id"]`` and runs it host-native. Sync
    because Opik ``evaluate()`` task fns cannot be async.
    """

    def regression_task_fn(item: dict[str, Any]) -> dict[str, Any]:
        probe = probes_by_id[item["probe_id"]]
        result = run_probe(probe)
        time.sleep(3.0)  # Gentle pacing to respect provider free-tier RPM limits
        return result

    return regression_task_fn


def run_probe(probe: RegressionProbe) -> dict[str, Any]:
    """Run one probe host-native in a fresh temp Workspace, returning a graded payload — never a raise."""
    workspace = Path(tempfile.mkdtemp(prefix="forge-regression-")).resolve()
    saved_settings: dict[str, Any] = {}
    try:
        saved_settings = _apply_settings_overrides(probe.settings_overrides)
        return _build_and_run(probe, workspace)
    except (
        Exception
    ) as exc:  # a fixture / setup / override failure must not abort the whole experiment
        logger.exception("[eval] regression probe setup failed for %s", probe.id)
        return _payload(None, file_state={}, probe=probe, agent_error=None, infra_error=str(exc))
    finally:
        _restore_settings(saved_settings)
        shutil.rmtree(workspace, ignore_errors=True)


def _apply_settings_overrides(overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Apply ``overrides`` to the global ``settings`` singleton, returning the prior values."""
    saved: dict[str, Any] = {}
    for key, value in overrides.items():
        if not hasattr(settings, key):
            logger.warning("[eval] ignoring unknown settings override: %s", key)
            continue
        saved[key] = getattr(settings, key)
        setattr(settings, key, value)
    return saved


def _restore_settings(saved: Mapping[str, Any]) -> None:
    """Restore the settings attributes :func:`_apply_settings_overrides` saved."""
    for key, value in saved.items():
        setattr(settings, key, value)


def _build_and_run(probe: RegressionProbe, workspace: Path) -> dict[str, Any]:
    """Seed the fixture, drive the agent, snapshot the tree — the happy body of :func:`run_probe`."""
    from contextlib import nullcontext

    max_retries = 4
    record: EvalRunRecord | None = None
    agent_error: str | None = None

    for attempt in range(max_retries):
        if attempt > 0:
            for child in workspace.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)

        probe.fixture(workspace)
        history = probe.message_history() if probe.message_history else None

        record = None
        agent_error = None
        context: AbstractContextManager[Any] = (
            probe.context(workspace) if probe.context else nullcontext()
        )
        try:
            with context:
                record = run_agent_once_sync(
                    probe.prompt,
                    cwd=workspace,
                    gate_mode=probe.gate_mode,
                    permission_rules=probe.permission_rules,
                    resolve_permission=probe.resolve_permission,
                    resolve_user_question=probe.resolve_user_question,
                    message_history=history,
                    max_requests=probe.max_requests,
                    enable_compaction=probe.enable_compaction,
                )
            agent_error = record.agent_error
        except Exception as exc:  # a crashed agent still grades — fail-with-reason, not skipped
            logger.exception("[eval] regression agent run raised for %s", probe.id)
            agent_error = f"agent run raised: {exc}"

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
                wait_time = float(match.group(1)) + 2.0
            elif (
                "503" in agent_error
                or "unavailable" in agent_error.lower()
                or "high demand" in agent_error.lower()
            ):
                wait_time = 10.0 * (attempt + 1)
            else:
                wait_time = 15.0 * (attempt + 1)

            logger.warning(
                "[eval] probe %s hit transient provider error; waiting %.1fs before retry (%d/%d): %s",
                probe.id,
                wait_time,
                attempt + 1,
                max_retries,
                agent_error[:120],
            )
            time.sleep(wait_time)
            continue
        break

    return _payload(
        record,
        file_state=_snapshot(workspace),
        probe=probe,
        agent_error=agent_error,
        infra_error=None,
    )


def _snapshot(workspace: Path) -> dict[str, str]:
    """Walk ``workspace`` and return ``{relative_path: utf8_body}`` for every regular file."""
    state: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if len(raw) > _MAX_SNAPSHOT_BYTES:
            state[relative] = f"[elided: {len(raw)} bytes > max {_MAX_SNAPSHOT_BYTES}]"
            continue
        try:
            state[relative] = raw.decode("utf-8")
        except UnicodeDecodeError:
            state[relative] = f"[binary: {len(raw)} bytes]"
    return state


def _payload(
    record: EvalRunRecord | None,
    *,
    file_state: dict[str, str],
    probe: RegressionProbe,
    agent_error: str | None,
    infra_error: str | None,
) -> dict[str, Any]:
    """The flat output dict the landed metrics + judges read."""
    tool_calls = (
        [{"name": call.name, "args": call.args} for call in record.tool_calls] if record else []
    )
    return {
        "output": record.output if record else "",
        "tool_calls": tool_calls,
        "steps": record.steps if record else 0,
        "input_tokens": record.input_tokens if record else 0,
        "output_tokens": record.output_tokens if record else 0,
        "denied_tools": record.denied_tools if record else [],
        "file_state": file_state,
        "probe_id": probe.id,
        "max_steps": probe.max_requests,
        "agent_error": agent_error,
        "infra_error": infra_error,
    }


def run_regression(
    *,
    probe_id: str | None = None,
    nb_samples: int | None = None,
    client: opik.Opik | None = None,
    experiment_name: str | None = None,
) -> EvaluationResult:
    """Run the filtered behavior regression suite as one Opik experiment (ADR-003 §3,4,6)."""
    import opik
    from opik.evaluation import evaluate

    from evals.harness.datasets import sync_regression_dataset

    all_probes = load_probes()
    selected = _runnable(_select_probes(all_probes, probe_id=probe_id))
    if not selected:
        raise RegressionSelectionError(
            f"no runnable regression probe matched (probe={probe_id!r}); {len(all_probes)} probe(s) available."
        )

    client = client or opik.Opik()
    dataset = sync_regression_dataset(selected, client=client)
    item_ids = _selected_item_ids(dataset, {probe.id for probe in selected})

    probes_by_id = {probe.id: probe for probe in all_probes}
    task_fn = make_regression_task_fn(probes_by_id)
    return evaluate(
        dataset=dataset,
        task=task_fn,
        scoring_metrics=_scoring_metrics(selected),
        experiment_config=experiment_config(),
        experiment_name=experiment_name,
        project_name=settings.eval_project_name,
        nb_samples=nb_samples,
        dataset_item_ids=item_ids or None,
        task_threads=1,
    )


def _select_probes(probes: list[RegressionProbe], *, probe_id: str | None) -> list[RegressionProbe]:
    """Filter loaded probes by exact ``probe_id`` (``None`` selects the whole suite)."""
    if probe_id is None:
        return probes
    return [probe for probe in probes if probe.id == probe_id]


def _runnable(probes: list[RegressionProbe]) -> list[RegressionProbe]:
    """Drop the skip-guarded probes from a run, logging each reason."""
    runnable: list[RegressionProbe] = []
    for probe in probes:
        if probe.skip_reason is not None:
            logger.info("[eval] skipping regression probe %s: %s", probe.id, probe.skip_reason)
            continue
        runnable.append(probe)
    return runnable


def _selected_item_ids(dataset: Any, selected_ids: set[str]) -> list[str]:
    """The dataset item ids whose ``probe_id`` is in ``selected_ids``."""
    items = dataset.get_items()
    return [
        item["id"]
        for item in items
        if item.get("probe_id") in selected_ids and item.get("id") is not None
    ]


def _scoring_metrics(probes: list[RegressionProbe]) -> list[BaseMetric]:
    """Wrap every selected probe's metrics in :class:`ProbeScopedMetric` (ADR-003 §6)."""
    return [ProbeScopedMetric(probe.id, metric) for probe in probes for metric in probe.metrics]


def experiment_config() -> dict[str, Any]:
    """The Opik ``experiment_config`` for a regression run: agent model, provider, git sha (ADR-003 §8)."""
    from evals.harness.benchmark import agent_model, git_sha

    return {
        "agent_model": agent_model(),
        "provider": "gemini",
        "git_sha": git_sha(),
        "harness": "regression",
    }
