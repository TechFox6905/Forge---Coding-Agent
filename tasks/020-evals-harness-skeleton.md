---

id: 020
feature: evals
status: done
------------

# Evals harness skeleton: package, settings, in-process agent driver

Depends on: none. Implements ADR-003 §1, §4.

## Scope

Create the top-level `evals/` package (outside `src/forge`, not shipped in the wheel).

**Layout:**

```text
evals/
├── __init__.py
├── __main__.py
├── run.py
└── harness/
    ├── __init__.py
    └── driver.py
```

**Driver (`evals/harness/driver.py`):**

Implement:

* `run_agent_once(...)` — async driver using Forge's real `build_agent()`, dependencies, `AgentTurnHandler`, and `Runner` execution lifecycle.
* `run_agent_once_sync(...)` — synchronous `asyncio.run()` wrapper for Opik `evaluate()`.

Support configurable:

* `cwd` (isolated workspace).
* Permission mode and permission rules.
* Permission and `AskUser` resolvers.
* Pre-filled message history.
* Maximum model requests.

Return a frozen `EvalRunRecord` containing:

* `output`
* `messages`
* `tool_calls`
* `steps`
* `input_tokens`
* `output_tokens`
* `denied_tools`
* `error`

Extract tool calls from Pydantic AI `ToolCallPart` objects and usage from `ModelResponse.usage`. Never use Opik traces as execution ground truth.

Default permission resolver must auto-deny in headless execution.

**Settings:**

Add to Forge settings and `.env.example`:

* `eval_judge_model = "groq/openai/gpt-oss-120b"`
* `eval_project_name = "forge-evals"`

**CLI (`evals/run.py`):**

* Create a Click group.
* Register `benchmark` and `regression` subcommand stubs.
* Support `python -m evals --help`.
* Initialize logging using Forge's existing convention.
* Keep Opik imports lazy.

**Dependencies:**

Add `opik` as a development dependency, not a production dependency.

**Tests (`tests/unit/evals/`):**

Use `FunctionModel` and existing Forge test fixtures. Cover driver execution, tool-call extraction, token aggregation, permission handling, message history, error handling, settings, and CLI.

## Acceptance Criteria

* [ ] Driver executes the real Forge agent.
* [ ] Tool calls and token usage are extracted correctly.
* [ ] Permission handling and custom resolvers work.
* [ ] Execution errors are distinguishable from successful empty responses.
* [ ] CLI works without importing Opik.
* [ ] Evaluation settings are configurable.
* [ ] Opik is a development dependency.
* [ ] Tests require no network or API credentials.
* [ ] `make ci` passes.

## Out of Scope

* Metrics and judge factory (021).
* Benchmark implementation (022–027).
* Regression implementation (028–032).
* Opik Test Suites (033).
* Online evaluation (034).
* Demo skills (035–036).
* Sandbox implementation (M8).

## Verification

```bash
uv run python -m evals --help
uv run pytest tests/unit/evals -v
uv run pytest --co -q
make ci
```
