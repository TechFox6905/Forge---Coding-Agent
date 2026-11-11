"""Unit tests for :mod:`evals.harness.metrics` (ADR-003 §4,7; task 021).

Tests all deterministic code metrics offline without Opik network calls.
"""

from __future__ import annotations

from pydantic import BaseModel

from evals.harness.metrics import (
    DiffLinesMetric,
    FileDiffLinesMetric,
    FileEqualsMetric,
    JsonSchemaMetric,
    MaxStepsMetric,
    NewFileNameMetric,
    OutputContainsMetric,
    ToolArgsMetric,
    ToolCalledMetric,
    ToolNotCalledMetric,
    ToolNotSucceededMetric,
    VerifyOracleMetric,
)


def test_tool_called_metric() -> None:
    metric = ToolCalledMetric("read")
    res_pass = metric.score(tool_calls=[{"name": "read", "args": {}}])
    assert res_pass.value == 1.0

    res_fail = metric.score(tool_calls=[{"name": "write", "args": {}}])
    assert res_fail.value == 0.0

    res_none = metric.score(tool_calls=None)
    assert res_none.value == 0.0


def test_tool_not_called_metric() -> None:
    metric = ToolNotCalledMetric("bash")
    res_pass = metric.score(tool_calls=[{"name": "read", "args": {}}])
    assert res_pass.value == 1.0

    res_fail = metric.score(tool_calls=[{"name": "bash", "args": {}}])
    assert res_fail.value == 0.0


def test_tool_args_metric() -> None:
    metric = ToolArgsMetric(
        "todo_write",
        lambda args: len(args.get("items", [])) >= 2,
        description="at least 2 items",
        name="test_todo_items",
    )
    res_pass = metric.score(tool_calls=[{"name": "todo_write", "args": {"items": ["a", "b"]}}])
    assert res_pass.value == 1.0

    res_fail = metric.score(tool_calls=[{"name": "todo_write", "args": {"items": ["a"]}}])
    assert res_fail.value == 0.0


def test_verify_oracle_metric() -> None:
    metric = VerifyOracleMetric()
    res_pass = metric.score(verify={"exit_code": 0, "stdout": "PASS"})
    assert res_pass.value == 1.0

    res_fail = metric.score(verify={"exit_code": 1, "stdout": "FAIL"})
    assert res_fail.value == 0.0

    res_stderr = metric.score(
        verify={"exit_code": 49, "stdout": "", "stderr": "Python was not found"}
    )
    assert res_stderr.value == 0.0
    assert "Python was not found" in res_stderr.reason

    res_invalid = metric.score(verify=None)
    assert res_invalid.value == 0.0


def test_max_steps_metric() -> None:
    metric = MaxStepsMetric()
    assert metric.score(steps=3, max_steps=5).value == 1.0
    assert metric.score(steps=6, max_steps=5).value == 0.0
    assert metric.score(steps=None, max_steps=5).value == 0.0
    assert metric.score(steps=0, max_steps=10, agent_error="status_code: 429").value == 0.0
    assert metric.score(steps=2, max_steps=10, infra_error="sandbox failed").value == 0.0


def test_diff_lines_metric() -> None:
    metric = DiffLinesMetric(max_lines=3)
    diff_ok = "--- a\n+++ b\n+1\n+2\n-3\n"
    assert metric.score(diff=diff_ok).value == 1.0

    diff_too_large = "--- a\n+++ b\n+1\n+2\n+3\n+4\n"
    assert metric.score(diff=diff_too_large).value == 0.0


def test_file_diff_lines_metric() -> None:
    baseline = "line 1\nline 2\nline 3\n"
    metric = FileDiffLinesMetric("file.txt", baseline, max_lines=2)

    state_ok = {"file.txt": "line 1\nline 2 changed\nline 3\n"}
    assert metric.score(file_state=state_ok).value == 1.0

    state_missing = {}
    assert metric.score(file_state=state_missing).value == 0.0


def test_file_equals_metric() -> None:
    metric = FileEqualsMetric("hello.txt", "expected content")
    assert metric.score(file_state={"hello.txt": "expected content"}).value == 1.0
    assert metric.score(file_state={"hello.txt": "wrong content"}).value == 0.0
    assert metric.score(file_state={}).value == 0.0


def test_new_file_name_metric() -> None:
    metric = NewFileNameMetric(
        suffix=".py",
        predicate=lambda name: name.startswith("forge_"),
        description="starts with forge_",
        name="test_prefix",
    )
    assert metric.score(file_state={"forge_agent.py": "code"}).value == 1.0
    assert metric.score(file_state={"bad_agent.py": "code"}).value == 0.0
    assert metric.score(file_state={"readme.md": "text"}).value == 0.0


def test_json_schema_metric() -> None:
    class Payload(BaseModel):
        status: str
        code: int

    metric = JsonSchemaMetric(Payload)
    assert metric.score(output='{"status": "ok", "code": 200}').value == 1.0
    assert metric.score(output='{"status": "ok"}').value == 0.0
    assert metric.score(output="not json").value == 0.0


def test_output_contains_metric() -> None:
    metric = OutputContainsMetric("secret-code")
    assert metric.score(output="Found secret-code in memory.").value == 1.0
    assert metric.score(output="Nothing here.").value == 0.0


def test_tool_not_succeeded_metric() -> None:
    metric = ToolNotSucceededMetric("write")
    # write called once, but denied once -> succeeded = 0 -> pass
    assert metric.score(tool_calls=[{"name": "write"}], denied_tools=["write"]).value == 1.0

    # write called once, not denied -> succeeded = 1 -> fail
    assert metric.score(tool_calls=[{"name": "write"}], denied_tools=[]).value == 0.0

    # write never called -> pass
    assert metric.score(tool_calls=[], denied_tools=[]).value == 1.0
