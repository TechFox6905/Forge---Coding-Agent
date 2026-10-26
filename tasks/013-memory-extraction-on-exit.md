---
id: 013-memory-extraction-on-exit
feature: m1-vanilla-agent
status: done
---

# Memory: extraction on exit

## Scope
A deliberately minimal memory-write loop ([ADR-0002 §8](../docs/adr/0002-milestone-1-vanilla-agent-architecture.md)): summarize the session into one sentence on quit, to be deepened in M4.

## Acceptance criteria
- [x] `memory/extract.py` runs on session end: one cheap Gemini call summarizes the conversation into a single sentence.
- [x] The sentence is appended (dated) to project-root `MEMORY.md` (created if absent), trimmed to the 200-line / 25 KB caps.
- [x] A summary failure is logged and non-fatal (never blocks exit).
- [x] The line is picked up by `memory.service` on the next session.

## Out of scope
- Forked-agent extractor, topic files, recall selector, compaction (M4).
