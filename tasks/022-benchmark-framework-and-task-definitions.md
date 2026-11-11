---

id: 022
feature: evals
status: done
depends_on: [020, 021]
----------------------

# Benchmark framework and task definitions

Implements ADR-003 §3 and §4.

## Scope

Create the benchmark task schema, loader, task definitions, and oracle validation under `evals/benchmark/`.

## Implementation

* Define a typed benchmark task format containing:

  * Task ID, name, difficulty, and description.
  * Initial workspace files and agent instructions.
  * Verification command and expected outcome.
  * Optional evaluation criteria.
* Implement a loader for tasks in `evals/benchmark/tasks/`.
* Add 20 benchmark tasks across easy, medium, and hard difficulty levels.
* Cover practical coding-agent workflows, including:

  * Git operations and conflict resolution.
  * JSON transformation and data processing.
  * SQLite analysis.
  * Test and dependency repair.
  * Secret handling.
  * CLI implementation.
* Run every task in an isolated temporary workspace.
* Keep verification assets hidden until agent execution finishes.
* Provide readable `verify.sh` scripts.
* Add oracle sanity checks:

  * Reference solution must pass.
  * Untouched workspace must fail.
* Reject malformed task definitions with actionable errors.

## Acceptance Criteria

* All 20 tasks load and validate.
* Tasks have isolated workspaces and independent verification.
* Verification assets are not accessible to the agent.
* Oracle sanity checks detect invalid verification scripts.
* Tests cover loading, validation, and oracle behavior.

## Verification

```bash
uv run pytest tests/unit/evals/benchmark -v
make ci
```
