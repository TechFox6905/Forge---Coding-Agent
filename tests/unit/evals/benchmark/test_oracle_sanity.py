"""Unit tests for evals.harness.oracle_sanity (ADR-003 §5; Task 022)."""

from __future__ import annotations

from pathlib import Path

from evals.harness.oracle_sanity import run_oracle
from evals.harness.task_loader import BenchmarkTask, load_benchmark_task


def test_mock_oracle_both_directions(tmp_path: Path) -> None:
    """An oracle must pass with solution and fail without it."""
    task_dir = tmp_path / "mock-task"
    task_dir.mkdir()
    setup_dir = task_dir / "setup"
    setup_dir.mkdir()
    solution_dir = task_dir / "solution"
    solution_dir.mkdir()
    verify_dir = task_dir / "verify"
    verify_dir.mkdir()

    (setup_dir / "target.txt").write_text("initial state\n", encoding="utf-8")
    (solution_dir / "target.txt").write_text("solved state\n", encoding="utf-8")
    (verify_dir / "verify.sh").write_text(
        "grep -q 'solved state' target.txt\n",
        encoding="utf-8",
    )

    task = BenchmarkTask(
        id="mock-task",
        prompt="Fix target.txt",
        max_steps=5,
        difficulty="easy",
        task_dir=task_dir,
    )

    # 1. Untouched setup must fail
    untouched_ws = tmp_path / "ws-untouched"
    untouched_ws.mkdir()
    fail_result = run_oracle(task, untouched_ws, with_solution=False)
    assert not fail_result.passed
    assert fail_result.exit_code != 0

    # 2. Gold solution overlay must pass
    solved_ws = tmp_path / "ws-solved"
    solved_ws.mkdir()
    pass_result = run_oracle(task, solved_ws, with_solution=True)
    assert pass_result.passed
    assert pass_result.exit_code == 0


def test_real_benchmark_task_oracle_sanity(tmp_path: Path) -> None:
    """Sample real task 001-find-and-replace oracle behaves correctly both ways."""
    from evals.harness.task_loader import BENCHMARK_TASKS_DIR

    task = load_benchmark_task(BENCHMARK_TASKS_DIR / "001-find-and-replace")

    ws_untouched = tmp_path / "ws1"
    ws_untouched.mkdir()
    fail_res = run_oracle(task, ws_untouched, with_solution=False)
    assert not fail_res.passed

    ws_solved = tmp_path / "ws2"
    ws_solved.mkdir()
    pass_res = run_oracle(task, ws_solved, with_solution=True)
    assert pass_res.passed


def test_python3_task_oracle_sanity(tmp_path: Path) -> None:
    """Sample real task 002-regex-extraction (which uses python3 in verify.sh) behaves correctly both ways."""
    from evals.harness.task_loader import BENCHMARK_TASKS_DIR

    task = load_benchmark_task(BENCHMARK_TASKS_DIR / "002-regex-extraction")

    ws_untouched = tmp_path / "ws_py3_1"
    ws_untouched.mkdir()
    fail_res = run_oracle(task, ws_untouched, with_solution=False)
    assert not fail_res.passed
    assert fail_res.exit_code != 49

    ws_solved = tmp_path / "ws_py3_2"
    ws_solved.mkdir()
    pass_res = run_oracle(task, ws_solved, with_solution=True)
    assert pass_res.passed
    assert pass_res.exit_code == 0
