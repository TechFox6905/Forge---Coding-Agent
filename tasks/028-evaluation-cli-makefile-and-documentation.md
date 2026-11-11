---

id: 028
feature: evals
status: done
depends_on: [022, 023, 024, 025, 026, 027]
------------------------------------------

# Evaluation CLI, Makefile, and documentation

Implements ADR-003 §9.

## Scope

Finalize evaluation commands, Makefile targets, and developer documentation.

## Implementation

* Finalize CLI commands:

  * `python -m evals benchmark`
  * `python -m evals regression`
  * `python -m evals online`
* Add Makefile targets:

  * `make eval-benchmark`
  * `make eval-regression`
* Support relevant options such as task selection, trial count, and baseline comparison.
* Document required environment variables:

  * `GEMINI_API_KEY`
  * `GROQ_API_KEY`
  * `OPIK_API_KEY`
  * `EVAL_PROJECT_NAME=forge-evals`
  * `EVAL_JUDGE_MODEL`
* Document setup, execution, metrics, reports, and troubleshooting.
* Keep evaluation commands manual; do not add them to `make ci`.
* Ensure evaluation tracing remains separate from live Forge tracing.

## Acceptance Criteria

* All evaluation CLI commands expose usable help.
* Makefile targets invoke the correct commands.
* Documentation explains setup and execution.
* Missing credentials produce actionable errors.
* `make ci` does not trigger live evaluations.

## Verification

```bash id="8q1v2m"
uv run python -m evals --help
uv run python -m evals benchmark --help
uv run python -m evals regression --help
make ci
```
