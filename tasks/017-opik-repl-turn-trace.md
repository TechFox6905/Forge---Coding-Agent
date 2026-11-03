---
id: 017-opik-repl-turn-trace
feature: opik-observability
status: done
---

# Opik observability — per-turn root span in the REPL

Tags: `observability`, `opik`, `tui`, `agent-loop`
Depends on: #016
Blocks: #018, #019

## Scope

Integrate Opik tracing into Forge's interactive REPL so every completed or aborted agent turn is represented by one root trace (ADR-002).
The root span must cover the complete turn lifecycle, including model requests, tool calls, deferred tool approval, and resume operations.
The Forge session ID identifies the Opik Thread.
- **Initialization** — call `observability.init_tracing()` once from the Forge application entrypoint, before the agent is built or executed.
  When tracing is active, emit the single INFO log through the existing logging infrastructure. Do not use `print()` for observability logging.
  When inactive, preserve existing application output.
- **Session ID propagation** — pass the current Forge session ID into `AgentTurnHandler`.
  Add an optional `session_id: str | None = None` parameter to its constructor. Use the existing session-log identifier rather than generating a separate tracing identifier.
  Keep the parameter optional for tests or execution paths without a session.
- **Root span per turn** — wrap the complete `AgentTurnHandler` turn lifecycle in:
  `observability.root_span("chat_turn", thread_id=self._session_id)`
  One handler invocation must correspond to one root span.
  Model requests, tool calls, and deferred approval/resume operations must remain within the same root span.
- **Root-span input** — record the user's prompt on the root span using the input attribute convention required by Opik's OTLP ingestion.
  The root span must contain conversation-level input, not just nested Pydantic AI span input.
- **Root-span output** — when the turn completes, call `observability.record_output()` with the final assistant response.
  Ensure output is recorded on the root span before it closes.
  Handle unsuccessful or aborted turns without incorrectly recording an incomplete response as a successful final output.
- **Async-generator lifecycle** — preserve the root span across yields and suspended execution.
  The span must close exactly once on:
  - Normal completion.
  - Exceptions.
  - Runner abort and generator closure.
  Verify the actual Forge runner lifecycle rather than assuming the behavior of another project's implementation.
  Context propagation must keep nested Pydantic AI spans associated with the active turn.
- **Inactive behavior** — when tracing is disabled, the root-span wrapper must be a no-op. No additional spans or application output should be produced.

## Acceptance Criteria

All tests must be hermetic. Use a fake API key for activation and `logfire.testing` with an in-memory exporter. Use `FunctionModel` or the appropriate existing model test seam.

- [x] One REPL turn produces exactly one `chat_turn` root span.
- [x] The root span has `thread_id` equal to the Forge session ID.
- [x] The root span records the user's prompt as input.
- [x] The root span records the final assistant response as output.
- [x] Model-request spans are nested under the root.
- [x] Tool spans are nested under the root.
- [x] Deferred tool approval and resume remain within the same trace.
- [x] Turn latency includes the approval wait.
- [x] LLM spans contain token usage attributes where supplied by the model.
- [x] Two turns in one session produce two root spans sharing the same `thread_id`.
- [x] Abort closes the root span exactly once.
- [x] Exceptions do not leak open spans.
- [x] Inactive tracing produces zero spans.
- [x] Inactive tracing produces no additional application output.
- [x] Initialization occurs before agent execution.
- [x] `make ci` passes without Opik credentials or network access.

## Out of scope

- Headless execution tracing.
- Subagent-specific tracing assertions.
- Compaction-specific tracing assertions.
- Documentation updates (018).
- Integration capstone and optional live smoke test (019).
- Evaluation workflows.
