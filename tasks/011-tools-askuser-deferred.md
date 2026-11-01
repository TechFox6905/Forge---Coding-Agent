---
id: 011-tools-askuser-deferred
feature: m1-vanilla-agent
status: done
---

# Tools: AskUser (deferred)

## Scope
The one blocking tool — the model asks the human a question, routed through the same deferred-pause path as approvals ([ADR-001 §2](../docs/adr/001-milestone-1-core-agent-architecture.md)).

## Acceptance criteria
- [x] `tools/askuser.py` `ask_user(question)` produces a deferred request that pauses the turn and surfaces the question in the TUI.
- [x] The user's typed answer becomes the tool result; only one AskUser in flight at a time.
- [x] Errors cleanly when no TUI is attached (headless-safe).
- [x] Tested with a fake resolver (no real terminal).

## Out of scope
- Structured multiple-choice questionnaires.
