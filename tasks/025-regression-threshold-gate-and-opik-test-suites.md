---

id: 025
feature: evals
status: done
depends_on: [024]
-----------------

# Regression threshold gate and Opik Test Suites

Implements ADR-003 §6.

## Scope

Add regression threshold enforcement, baseline comparison, and Opik Test Suites integration.

## Implementation

* Define configurable regression thresholds.
* Compare current aggregate scores against a stored baseline.
* Fail the regression command when:

  * Aggregate score falls below the configured threshold.
  * Regression exceeds the allowed baseline delta.
* Produce a report showing baseline, current score, and delta.
* Integrate Opik Test Suites using:

  * `get_or_create_test_suite()`
  * `run_tests()`
  * `pass_rate`
* Run a representative subset of regression probes through Opik Test Suites.
* Keep pytest threshold checks as the local CI gate.
* Do not add live evaluation calls to `make ci`.

## Acceptance Criteria

* Threshold violations return a non-zero exit code.
* Baseline comparisons report score changes.
* Opik Test Suites record probe results and pass rate.
* Missing baselines are handled explicitly.
* Unit tests cover threshold and comparison logic without API calls.

## Verification

```bash id="4v9k2a"
uv run python -m evals regression --help
uv run pytest tests/unit/evals/regression -v
make ci
```
