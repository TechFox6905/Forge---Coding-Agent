---

id: 027
feature: evals
status: done
depends_on: [020, 021]
----------------------

# Demo skills

Implements ADR-003 §2.

## Scope

Create human-judged demo scenarios demonstrating Forge's capabilities under `evals/demos/`.

## Implementation

* Add demo scenarios covering:

  * File reading and code exploration.
  * File creation and precise editing.
  * Permission approval and denial.
  * Task planning and execution.
  * Memory usage and grounded responses.
  * Multi-step tool workflows.
* Each demo must include:

  * Scenario description and objective.
  * Initial workspace or required setup.
  * Steps to execute.
  * Expected behavior and evaluation criteria.
* Keep demos reproducible and suitable for human review.
* Reuse the real Forge agent and existing tool architecture.
* Document any manual setup or external API requirements.

## Acceptance Criteria

* Demo scenarios are documented and executable.
* Expected behavior is clearly defined.
* Demos do not depend on benchmark verification assets.
* Results can be reviewed consistently by a human evaluator.

## Verification

```bash id="2k9p4m"
uv run pytest tests/unit/evals -v
make ci
```
