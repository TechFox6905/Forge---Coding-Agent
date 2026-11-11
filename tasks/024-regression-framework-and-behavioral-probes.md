---

id: 024
feature: evals
status: done
depends_on: [020, 021]
----------------------

# Regression framework and behavioral probes

Implements ADR-003 §5 and §6.

## Scope

Create the regression evaluation framework and behavioral probe dataset under `evals/regression/`.

## Implementation

* Define a typed regression probe format containing ID, category, input, expected behavior, and evaluation criteria.
* Implement a loader for regression probes.
* Create 15 behavioral probes covering:

  * Tool selection and execution discipline.
  * Read vs Bash and precise edit behavior.
  * Planning and task management.
  * Permission approval and denial handling.
  * Destructive operation caution.
  * Memory obedience and grounded responses.
  * Hallucinated file prevention.
  * Output format and JSON contracts.
* Use deterministic assertions wherever possible.
* Use the Groq LLM judge only for subjective behavioral criteria.
* Mark unsupported capabilities as deferred or skipped with explicit reasons. Do not report them as passing.
* Integrate probes with Opik `evaluate()` and record individual scores.

## Acceptance Criteria

* Probe definitions load and validate.
* Supported probes execute against the real Forge agent.
* Deterministic and LLM-judged results remain distinguishable.
* Unsupported probes are explicitly reported.
* Results are recorded in Opik.
* Tests run offline using mocked models.

## Verification

```bash id="1klm9p"
uv run pytest tests/unit/evals/regression -v
make ci
```
