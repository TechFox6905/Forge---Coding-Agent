# 001. Milestone 1 Architecture — Core Architecture and Engineering Decisions

**Status:** Accepted

## Context

Milestone 1 establishes the first functional vertical of `forge`: a terminal REPL that runs a **Pydantic AI ReAct loop** using **Gemini**, supported by a core set of tools, **ask-on-every-tool** permissions, mid-turn **steering**, a memory layer, and a replayable session log.

The architecture was examined decision by decision and cross-validated against three reference harnesses—claude-code, opencode, and pi—from the research wiki. Since these decisions are closely connected, the agent loop, permissions, queueing, TUI, memory, and persistence are documented together in **a single milestone-architecture ADR** rather than separate ADRs for individual tasks.

The ordered implementation tasks are available in [`tasks/`](../../tasks/) under the `m1-vanilla-agent` feature. 

## Decision

M1 will be implemented as a standalone Python package with the following foundational architectural decisions:

1. **Agent loop using Pydantic AI and Gemini.** The model will be initialized through the `google-gla:` API-key configuration path, which reads `GEMINI_API_KEY`. The model identifier will be configurable through `settings.gemini_model`. Pydantic AI will manage the ReAct loop, while streaming will be handled through `agent.iter()`. *(M2 will replace the provider with OpenRouter/Modal through the same factory.)*

2. **HITL through deferred tool requests.** Both tool approvals and `AskUser` interactions will use Pydantic AI's `DeferredToolRequests` and `DeferredToolResults`. Each turn will be divided into multiple legs: `iter → deferred pause → resume`. Although the surveyed harnesses perform approval checks *inline*, `agent.iter()` treats a run as one atomic turn. Deferred execution provides the mechanism required to **support mid-turn steering** by appending a steering message before resuming execution. It is also serializable, preparing the architecture for **M7** Kitaru-based durable HITL and **M9** remote deployment.

3. **Permissions requiring approval for every tool call.** `PermissionGate.check()` will return `allow`, `ask`, or `deny`, along with a `mode` field. Tools will include a `read_only` flag, although read-only tools will still require approval in v1. This design supports future **M3** permission modes (`default/plan/edit/bypass`), automatic approval for read-only operations, and persisted permission rules without requiring an architectural rewrite.

4. **Two-queue interaction model.** A **steering queue** will be processed *before each model-request leg*. Messages will be injected at execution boundaries rather than interrupting an active stream or tool. A separate **follow-up queue** will be processed *only when the agent reaches a boundary where it would otherwise stop*. While the agent is busy, pressing `Enter` will submit steering input, whereas `Alt+Enter` will submit a follow-up. A single-flight lock will cover the entire multi-leg turn, with the execution phase established before the first `await`. This mechanism serves as the architecture's *Priority Gate*, using pi as the reference implementation.

5. **Cooperative abort mechanism.** Pressing `Esc` will set an abort flag, causing the current turn to stop at the next execution boundary. A runaway `bash` operation will be constrained by `bash_timeout_s`. Immediate or hard cancellation is postponed until **M8** sandboxing, where process termination can be defined and managed reliably.

6. **TUI using `patch_stdout()` and concurrent `prompt_async()`.** The terminal interface will use append-style Rich output above a persistent input line instead of a full-screen renderer. Tool calls will be displayed after completion to minimize visual flicker. Later migration to a full-screen or differential renderer will require changes only within the `tui` layer.

7. **Core tool set.**

   * **File I/O:** `read` will support line-based pagination, while `write` and `edit` will require permission checks. The `edit` tool will remove BOM characters and normalize CRLF/LF line endings. It will attempt an exact match first, followed by whitespace-tolerant fuzzy matching, and will require exactly one matching result. Zero or multiple matches will trigger `ModelRetry`.
   * **Bash:** Execution will have a timeout and output truncation limits of 2,000 lines and 50 KB, with overflow redirected to a temporary file. Execution will pass through a `tools/exec.py` executor interface to support the M8 transition to sandboxing.
   * **Tasks:** An in-memory task manager following the TodoWrite-style approach.
   * **Web:** `httpx` GET requests will retrieve content, which will then be converted from HTML to Markdown to reduce token consumption.
   * **AskUser:** User interactions will use deferred execution.

   Tool execution will remain sequential in v1. Parallel read-only operations and per-realpath mutation queues will be introduced in M3.

8. **Memory management.** The agent will load `AGENTS.md` and `MEMORY.md` while traversing from the current working directory toward the repository root, with the current working directory taking precedence. Loaded content will be restricted to **200 lines and 25 KB**, then injected into the agent's instructions. When a session ends, a single low-cost Gemini call will append a dated, one-sentence summary to `MEMORY.md`. This intentionally minimal implementation serves as a teaching version; production-grade memory extraction and compaction are deferred to **M4**.

9. **Session persistence.** Sessions will be recorded in an append-only **JSONL** log using Pydantic AI's message serialization. The log will contain a header on line 0 followed by typed entries and will be stored at `.forge/sessions/<ts>_<uuid>.jsonl`. Running `forge --resume` will replay the most recent session. SQLite-based persistence and Kitaru durability will be introduced later.

10. **Engineering conventions defined in `AGENTS.md`.**

    * Call `init_logger()` at the module level in entrypoints.
    * Maintain a singleton `settings` instance using `pydantic-settings`.
    * Use asynchronous execution for I/O and synchronous execution for CPU-bound operations.
    * Import infrastructure directly instead of introducing unnecessary abstractions.
    * Keep the `tests/` directory aligned one-to-one with `src/`.
    * Configure `filterwarnings=["error"]`.
    * Test model interactions with `TestModel` and `FunctionModel`, ensuring CI tests do not require network access.

## Consequences

* **Intentional differences from the surveyed harnesses:** HITL uses deferred execution instead of inline approval, and the TUI uses `patch_stdout` instead of a full-screen renderer. These are deliberate trade-offs. Deferred execution enables mid-turn steering and durable HITL, while the append-style TUI keeps the initial implementation simple and allows a clean upgrade path.

* **Turns are divided into multiple `iter` legs.** The single-flight lock must remain active throughout the entire turn. Steering messages can only be applied at model-request boundaries, never during an active tool execution or stream. A turn cannot be redirected until the current tool or stream has finished.

* **The append-style TUI does not maintain a dynamically rewritten live region.** Features such as spinners and partially rendered tool calls are therefore unavailable in M1. This limitation is acceptable for the initial milestone.

* **Minimal memory write-back is an intermediate implementation.** It provides a foundation for later improvements but is not intended to serve as a production-ready memory system.

* **Architectural extension points are reserved for later milestones:**

  * Provider replacement through the existing factory — **M2**.
  * Permission modes and the agent catalog — **M3**.
  * Memory compaction — **M4**.
  * Executor-to-sandbox migration — **M8**.
  * Deferred-to-durable and remote HITL — **M7/M9**.
  * A single tracing entry point within `run_turn` — **M11**.
  * Migration from a flat tool registry to MCP — **M12**.

* **Implementation risks requiring verification:**

  * Confirm the API-key keyword argument expected by Pydantic AI's `GoogleProvider`, verify the currently supported Gemini model identifier, and validate that a steering user message can be appended during a deferred resume (task 004).
  * Verify the exact message-serialization API provided by Pydantic AI (task 014).
  * Ensure the terminal prompt remains correctly positioned and usable during heavy streaming output (task 002).
