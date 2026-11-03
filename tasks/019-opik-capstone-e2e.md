---
id: 019-opik-capstone-e2e
feature: opik-observability
status: done
---

# Opik observability — integration capstone and span-tree verification

Tags: `observability`, `opik`, `test`
Depends on: #016, #017
Blocks: —

## Scope

Create an integration capstone proving that the actual Forge execution stack produces the expected Opik span hierarchy.
Add:
`tests/integration/test_observability_capstone.py`
Follow the existing Forge integration-test conventions.
Use the real application and execution components. Replace only the model boundary and telemetry exporter.
- **Hermetic integration slice** — no real Opik credentials or network access.
  Exercise the real:
  - Agent construction.
  - Runner and turn lifecycle.
  - AgentTurnHandler.
  - Tool execution and deferred approval flow.
  - Session handling.
  - Observability initialization and root-span integration.
  Fake:
  - Model responses using `FunctionModel` or the existing model test seam.
  - Opik API key for activation.
  - Span exporter using `logfire.testing` in-memory utilities.
- **Span-tree assertions** — verify:
  1. **Turn root:** one `chat_turn` root span with the correct session `thread_id`.
  2. **Root input/output:** prompt and final assistant response are recorded on the root.
  3. **Model spans:** Pydantic AI model-request spans are children of the turn root.
  4. **Tool spans:** tool execution spans are nested under the correct turn.
  5. **Token usage:** LLM spans expose `gen_ai.usage.*` attributes when usage is supplied.
  6. **Deferred approval:** approval and resume remain inside the same root trace.
  7. **Session grouping:** multiple turns in one session share a `thread_id` but produce separate traces.
  8. **No-op behavior:** without an API key, the same execution produces zero exported spans.
- **Memory write-back** — verify global Pydantic AI instrumentation captures memory write-back calls. If memory write-back executes outside an active turn, verify it produces its own trace rather than incorrectly attaching to an unrelated turn.
- **Abort safety** — verify that aborted turns close their root spans without leaking unfinished spans or asynchronous tasks.
- **Optional live Opik smoke test** — add a credential-guarded test that:
  - Skips when `OPIK_API_KEY` is unset.
  - Uses a real configured exporter.
  - Performs one minimal real model operation.
  - Verifies export completes without error.
  The live test must not be required for ordinary CI. Do not assert Opik-side UI content.
- **Test isolation** — use `logfire.testing` provider isolation and `reset_tracing()` where appropriate. Prevent process-global telemetry configuration from leaking between tests.
- **Module documentation** — document which boundaries are real and which are faked.

## Acceptance Criteria

- [x] The integration capstone exercises the real Forge execution stack.
- [x] Exactly one root span is produced per REPL turn.
- [x] Root span has the correct `thread_id`.
- [x] Root input and output are recorded.
- [x] Model-request spans nest under the turn root.
- [x] Tool spans nest under the turn root.
- [x] Token usage is present on scripted LLM spans.
- [x] Deferred approval/resume remains in the same trace.
- [x] Multiple turns share a session Thread but produce distinct traces.
- [x] Memory write-back instrumentation is verified.
- [x] No-key execution produces zero exported spans.
- [x] Abort and exception paths do not leak spans.
- [x] Optional live smoke skips cleanly without credentials.
- [x] Tests pass under `filterwarnings=["error"]`.
- [x] `make ci` passes without credentials or network access.

## Out of scope

- Headless execution traces.
- Subagent-specific span-tree assertions.
- Compaction-specific assertions.
- Evaluation datasets, experiments, and automated scoring.
- Deployed remote-stack verification.
