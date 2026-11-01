---
id: 004-agent-chat-only
feature: m1-vanilla-agent
status: done
---

# Agent loop: chat-only (Pydantic AI + Gemini)

## Scope
The Pydantic AI agent on Gemini with streaming, no tools — the first real round-trip. Replaces the stub turn handler. See [ADR-001 §1–2](../docs/adr/001-milestone-1-core-agent-architecture.md).

## Acceptance criteria
- [x] `agent/factory.py` builds `Agent(output_type=[str, DeferredToolRequests], deps_type=AgentDeps)` on Gemini via the `google-gla:` API-key path; model id from `settings.gemini_model`.
- [x] `agent/loop.py` (`AgentTurnHandler`) drives `agent.iter()`, streams `TextPartDelta` → `AssistantTextDelta` events, drains steering before each model-request leg; `message_history` carries across turns.
- [x] Unit tests use `pydantic_ai.models.test.TestModel`/`FunctionModel` (no network). `uv run forge` wiring verified offline against `TestModel`/`FunctionModel`; — [ ] [HUMAN] hold a real Gemini chat (needs `GEMINI_API_KEY`, not available in this env).
- [x] Confirmed against the installed SDK: `GoogleProvider(api_key=...)` (google-gla, not Vertex), model id `gemini-2.5-flash`, `agent.iter()` + node `stream()` + `PartDeltaEvent`/`TextPartDelta`/`ThinkingPartDelta`, `message_history` carry-over. Steering append before each model request is confirmed; a steering user-message at a *real* `DeferredToolRequests` resume is deferred to task 005 (chat-only has no tools to defer) — see log.

## Out of scope
- Tools, the permission gate (task 005+).

## Dependencies
- Adds `pydantic-ai` (pulls `google-genai`).