"""Unit tests for evals.harness.task_loader (ADR-003 §3,4; Task 022)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from evals.harness.task_loader import (
    BENCHMARK_TASKS_DIR,
    BenchmarkTask,
    BenchmarkTaskError,
    load_benchmark_task,
    load_benchmark_tasks,
)


def test_load_all_20_benchmark_tasks() -> None:
    """All 20 authored benchmark tasks must load and pass contract validation."""
    tasks = load_benchmark_tasks(BENCHMARK_TASKS_DIR)
    assert len(tasks) == 20

    ids = [task.id for task in tasks]
    assert len(set(ids)) == 20, "Every task id must be unique"

    difficulties = {task.difficulty for task in tasks}
    assert difficulties == {"easy", "medium", "hard"}

    for task in tasks:
        assert isinstance(task, BenchmarkTask)
        assert task.prompt.strip(), f"{task.id} has blank prompt"
        assert task.max_steps > 0, f"{task.id} has invalid max_steps"
        assert task.verify_script.is_file(), f"{task.id} is missing verify.sh"
        assert task.setup_dir.is_dir(), f"{task.id} is missing setup dir"
        assert task.solution_dir.is_dir(), f"{task.id} is missing solution dir"


def test_load_benchmark_task_single() -> None:
    """load_benchmark_task correctly loads and parses one task."""
    task_dir = BENCHMARK_TASKS_DIR / "001-find-and-replace"
    task = load_benchmark_task(task_dir)

    assert task.id == "001-find-and-replace"
    assert task.difficulty == "easy"
    assert task.max_steps > 0
    assert "config.ini" in task.prompt
    assert task.task_dir == task_dir


def test_task_loader_rejects_missing_task_yaml(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkTaskError, match=r"missing task\.yaml"):
        load_benchmark_task(tmp_path)


def test_task_loader_rejects_missing_verify_sh(tmp_path: Path) -> None:
    yaml_content = {
        "id": "test-task",
        "prompt": "Fix the bug",
        "max_steps": 5,
        "difficulty": "easy",
    }
    (tmp_path / "task.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")

    with pytest.raises(BenchmarkTaskError, match="missing hidden oracle"):
        load_benchmark_task(tmp_path)


def test_task_loader_rejects_blank_prompt(tmp_path: Path) -> None:
    verify_dir = tmp_path / "verify"
    verify_dir.mkdir()
    (verify_dir / "verify.sh").write_text("exit 0", encoding="utf-8")

    yaml_content = {
        "id": "test-task",
        "prompt": "   ",
        "max_steps": 5,
        "difficulty": "easy",
    }
    (tmp_path / "task.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")

    with pytest.raises(BenchmarkTaskError, match="violates the contract"):
        load_benchmark_task(tmp_path)


def test_task_loader_rejects_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "task.yaml").write_text("id: [broken yaml", encoding="utf-8")

    with pytest.raises(BenchmarkTaskError, match="not valid YAML"):
        load_benchmark_task(tmp_path)


def test_task_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    verify_dir = tmp_path / "verify"
    verify_dir.mkdir()
    (verify_dir / "verify.sh").write_text("exit 0", encoding="utf-8")

    yaml_content = {
        "id": "test-task",
        "prompt": "Do it",
        "max_steps": 5,
        "difficulty": "easy",
        "nonexistent_extra_field": "bad",
    }
    (tmp_path / "task.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")

    with pytest.raises(BenchmarkTaskError, match="violates the contract"):
        load_benchmark_task(tmp_path)


def test_load_benchmark_tasks_missing_root(tmp_path: Path) -> None:
    assert load_benchmark_tasks(tmp_path / "nonexistent") == []
