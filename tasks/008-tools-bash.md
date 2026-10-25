---
id: 008-tools-bash
feature: m1-vanilla-agent
status: done
---

# Tools: bash execution

## Scope
Gated shell execution with a local-executor seam (M8 swaps it for a sandbox).

## Acceptance criteria
- [x] `tools/exec.py` defines the executor seam; `tools/bash.py` runs via `asyncio` subprocess.
- [x] `settings.bash_timeout_s` enforced; output truncated via `tools/truncate.py` (2000 lines / 50 KB) with overflow spilled to a temp-file path in the result. (Timeout path now returns the documented partial output — fixed in the SWE Fixes log entry, re-verified by the Tester 2026-06-19 21:40.)
- [x] Gated (no dangerous-command classifier in v1 — human approves every call).

## Out of scope
- Background jobs; OS sandbox / dangerous-command classifier (M8).