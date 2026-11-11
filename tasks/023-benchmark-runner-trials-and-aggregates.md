---

id: 023
feature: evals
status: done
depends_on: [020, 021, 022]
---------------------------

# Benchmark runner, trials, and aggregates

Implements ADR-003 §3, §4, and §7.

## Scope

Implement benchmark execution, repeated trials, Opik evaluation integration, and aggregate reporting.

## Implementation

* Implement the benchmark runner under `evals/benchmark/runner.py`.
* Load tasks and execute Forge through `run_agent_once()`.
* Create a fresh temporary workspace for every trial.
* Inject verification assets only after agent execution.
* Execute `verify.sh` and record the outcome.
* Collect agent output, errors, tool calls, steps, token usage, duration, and verification results.
* Add `--trials K` to the benchmark CLI.
* Integrate Opik `evaluate()` with `trial_count=K`.
* Calculate:

  * pass@1
  * pass@k
  * pass^k
  * Flakiness rate
  * Cost per successful task
* Record experiment configuration: agent model/provider, judge model, Git SHA, trial count, and timestamp.
* Attach aggregate feedback scores to the Opik experiment.
* Account for judge costs separately from agent costs.
* Continue recording individual task failures without aborting the complete benchmark run.

## Acceptance Criteria

* Individual tasks and the complete benchmark execute successfully.
* Every trial uses an isolated workspace.
* Verification runs after agent execution.
* Trial results and aggregate metrics are recorded correctly.
* Opik receives experiment metadata and aggregate scores.
* Unit tests validate execution and metric calculations without live API calls.

## Verification

```bash
uv run python -m evals benchmark --help
uv run pytest tests/unit/evals/benchmark -v
make ci
```
