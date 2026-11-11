---

id: 026
feature: evals
status: done
depends_on: [020, 021, 024, 025]
--------------------------------

# Online evaluation

Implements ADR-003 §8.

## Scope

Add a minimal online evaluation workflow using Forge's existing Opik traces.

## Implementation

* Configure one documented Opik online LLM-as-a-judge evaluation rule.
* Evaluate a small set of quality criteria, such as:

  * Answer groundedness.
  * Response relevance.
  * Tool-use correctness.
* Add a script that retrieves live threads from the Forge Opik project.
* Run a scripted `evaluate_threads` pass over retrieved threads.
* Keep online evaluation separate from offline benchmark and regression runs.
* Document configuration, execution, and required credentials.

## Acceptance Criteria

* Online evaluation rule is documented and configurable.
* Script evaluates threads from the live Forge project.
* Evaluation results are visible in Opik.
* Missing credentials or project configuration produce actionable errors.
* Online evaluation is never triggered by `make ci`.

## Verification

```bash id="6m3x2q"
uv run python -m evals online --help
uv run pytest tests/unit/evals -v
make ci
```
