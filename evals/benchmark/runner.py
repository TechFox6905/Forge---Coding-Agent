"""Benchmark runner module (ADR-003 §3,4,7; Task 023).

Re-exports the benchmark runner, task function builder, and experiment configuration
from ``evals.harness.benchmark``.
"""

from __future__ import annotations

from evals.harness.benchmark import (
    BenchmarkSelectionError,
    BenchmarkTaskFn,
    agent_model,
    experiment_config,
    git_sha,
    make_benchmark_task_fn,
    run_benchmark,
)

__all__ = [
    "BenchmarkSelectionError",
    "BenchmarkTaskFn",
    "agent_model",
    "experiment_config",
    "git_sha",
    "make_benchmark_task_fn",
    "run_benchmark",
]
