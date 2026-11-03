---
id: 018-opik-docs-and-e2e-rows
feature: opik-observability
status: done
---

# Opik observability — documentation and manual QA

Tags: `observability`, `opik`, `docs`
Depends on: #016, #017
Blocks: #019

## Scope

Document the shipped Opik observability integration (ADR-002). No product-code changes.
- **README** — add a Monitoring / Observability (Opik) section documenting:
  - Enablement through `OPIK_API_KEY`.
  - Optional self-hosted configuration through `OPIK_URL_OVERRIDE`.
  - Workspace and project configuration.
  - One trace per REPL turn.
  - Session grouping through the Forge session ID.
  - Model requests and tool calls.
  - Deferred approval/resume within the same turn trace.
  - Root-span input/output and conversation display.
  - Token usage and cost availability for supported models.
  - Memory write-back instrumentation.
  - Silent no-op behavior when the API key is absent.
  - Evaluation workflows as a future milestone.
- **AGENTS.md** — add an Opik observability entry to the appropriate testing/manual-QA section.
  Explain how to enable tracing and what a successful run looks like:
  - Tracing initialization is logged once when active.
  - A REPL turn produces one `chat_turn` root span.
  - The root span is associated with the session Thread.
  - Model and tool spans appear under the turn.
  - Prompt and final response appear as root-level input/output.
  - Deferred approval/resume remains in the same trace.
- **`.env.example`** — verify the Opik block is commented out and documents all four settings.
- **ADR cross-reference** — use ADR-002 as the source of truth. Do not modify unrelated accepted ADRs or introduce stale references.

## Acceptance Criteria

- [x] README documents enablement, configuration, behavior, and no-op default.
- [x] AGENTS.md contains a manual-QA entry matching the actual Forge implementation.
- [x] `.env.example` accurately documents the four settings.
- [x] No headless execution behavior is documented.
- [x] No unsupported subagent or compaction behavior is claimed.
- [x] Evaluation is clearly outside this milestone.
- [x] Documentation contains no stale references.
- [x] `make ci` passes.

## Out of scope

- Product code.
- Automated integration tests (019).
- Evaluation implementation.
