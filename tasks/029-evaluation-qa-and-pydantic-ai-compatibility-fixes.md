---

id: 029
feature: evals
status: done
depends_on: [020, 021, 022, 023, 024, 025, 026, 027, 028]
---------------------------------------------------------

# Evaluation QA and Pydantic AI compatibility fixes

Implements ADR-003 implementation-wide QA.

## Scope

Run end-to-end evaluation QA and resolve integration issues across the evaluation suite.

## Implementation

* Validate the in-process driver against the current Forge architecture.
* Verify Pydantic AI message-history, `ToolCallPart`, and usage extraction.
* Check permission handling and headless execution.
* Validate benchmark isolation and hidden verification assets.
* Verify regression metrics, Opik integration, and threshold behavior.
* Check Groq judge configuration and error handling.
* Resolve dependency conflicts and Pydantic AI API compatibility issues.
* Add regression tests for every discovered fix.
* Avoid modifying frozen M1 architecture or existing ADR-002 tracing behavior.

## Acceptance Criteria

* Evaluation unit and integration tests pass.
* Driver behavior matches the actual Forge execution lifecycle.
* No existing Forge functionality or tracing behavior regresses.
* Dependency and API compatibility issues are resolved.
* No live API calls are required by `make ci`.

## Verification

```bash id="9f2k7w"
uv run pytest tests/unit/evals -v
uv run pytest tests/integration -v
make ci
```
