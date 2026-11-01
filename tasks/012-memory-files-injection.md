---
id: 012-memory-files-injection
feature: m1-vanilla-agent
status: done
---

# Memory: files layer + injection

## Scope
Read the project memory files and inject them into the agent's instructions ([ADR-001 §8](../docs/adr/001-milestone-1-core-agent-architecture.md)).

## Acceptance criteria
- [x] `memory/files.py` discovers `AGENTS.md` + `MEMORY.md` walking cwd→repo-root (cwd-most wins); `CLAUDE.md` skipped.
- [x] `memory/service.py` `assemble_memory(cwd)` concatenates with provenance headers; `MEMORY.md` capped at 200 lines AND 25 KB with a visible truncation note when exceeded.
- [x] Injected at prompt-build time via a dynamic `@agent.instructions` hook; verified via `result.all_messages()`.
- [x] Missing files are skipped, not errors.

## Out of scope
- Memory write-back (task 013); `@`-import resolution; user-global `~/.forge/`.
