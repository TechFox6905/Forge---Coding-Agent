---
id: 005-permission-gate-deferred
feature: m1-vanilla-agent
status: done
---

# Permission gate (deferred approval)

## Scope
The ask-on-every-tool gate per [ADR-001 §2–3](../docs/adr/001-milestone-1-core-agent-architecture.md), wired into the loop's `DeferredToolRequests` → approve → resume path. Tested with one trivial gated tool.

## Acceptance criteria
- [x] `permissions/gate.py` `check()` returns `allow/ask/deny` and carries a `mode` field (always asks in v1); `entities/permissions.py` defines `PermissionRequest`/`PermissionDecision`.
- [x] A gated tool pauses the run, emits `PermissionRequested`, and resumes with `DeferredToolResults`.
- [x] A denial is fed back to the model as a tool result (`ToolDenied`); tools carry a `read_only` flag (tagged, still asked in v1).
- [x] The single-flight lock spans the full multi-leg turn; tested with `TestModel(call_tools=...)`.

## Out of scope
- Modes `default/plan/edit/bypass`, read-only auto-allow, persisted rules.