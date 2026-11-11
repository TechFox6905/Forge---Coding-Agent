---

id: 030
feature: evals
status: done
depends_on: [029]
-----------------

# Final evaluation review and rollup

Implements final ADR-003 acceptance review.

## Scope

Perform a final implementation review and verify that the evaluation suite satisfies ADR-003.

## Implementation

* Review all evaluation modules, task definitions, probes, and demos.
* Verify benchmark and regression commands end to end.
* Check Opik experiments, Test Suites, and online evaluation integration.
* Review metric calculations, thresholds, and baseline reporting.
* Confirm environment configuration and documentation.
* Remove duplicated code, unused utilities, and temporary artifacts.
* Check package boundaries: `evals/` remains outside `src/forge` and is not shipped in the Forge wheel.
* Record known limitations and deferred capabilities.
* Produce a final implementation summary with test results.

## Acceptance Criteria

* All ADR-003 requirements are implemented or explicitly marked deferred.
* Benchmark, regression, and online evaluation workflows are documented.
* Existing Forge tests and `make ci` pass.
* Evaluation code is isolated from the production package.
* Remaining limitations are documented.
* Final review summary is available.

## Verification

```bash id="4w7n2c"
uv run pytest
make ci
uv run python -m evals --help
```
