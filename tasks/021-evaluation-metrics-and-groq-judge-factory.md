---

id: 021
feature: evals
status: done
depends_on: [020]
-----------------

# Evaluation metrics and Groq judge factory

Implements ADR-003 §5 and §6.

## Scope

Create `evals/harness/metrics.py` and `evals/harness/judges.py`.

## Implementation

* Implement deterministic metrics using DeepEval-compatible metric interfaces:

  * Task success
  * Tool usage and execution
  * Permission compliance
  * Output correctness
* Keep code-verifiable checks deterministic; do not use an LLM judge for them.
* Create a reusable GEval judge factory using DeepEval and LiteLLM.
* Default judge: `groq/openai/gpt-oss-120b`.
* Support `groq/openai/gpt-oss-20b` and `EVAL_JUDGE_MODEL` override.
* Read credentials from `GROQ_API_KEY`.
* Use the judge only for subjective criteria such as quality, groundedness, and minimality.
* Keep judge configuration independent of Forge's production Gemini model.

## Acceptance Criteria

* Metrics return consistent, structured results.
* Judge factory supports configured Groq models.
* Missing credentials produce a clear error.
* Unit tests do not make live API calls.

## Verification

```bash
uv run pytest tests/unit/evals -v
make ci
```
