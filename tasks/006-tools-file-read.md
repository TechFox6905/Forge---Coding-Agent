---
id: 006-tools-file-read
feature: m1-vanilla-agent
status: done
---

# Tools: file read + glob + grep

## Scope
Read-only file tools and the shared output-truncation helper + the tool registry.

## Acceptance criteria
- [x] `tools/truncate.py`: dual cap (2000 lines OR 50 KB, snap to line boundary), overflow spilled to a temp file whose path is returned.
- [x] `tools/files.py`: `read` (line-paginated `offset`/`limit`, numbered lines, truncated), `glob`, `grep` — all honor `ctx.deps.cwd`, tagged `read_only=True`. **FIXED (SWE): `glob`/`grep` now reject `..`/absolute patterns up front and drop any match resolving outside cwd (incl. in-tree symlinks) — see SWE fix log.**
- [x] `tools/registry.py` registers tools on the agent (flat registry, each tagged read-only or not).
- [x] Missing path → model-readable `ModelRetry`.

## Out of scope
- Write/edit (task 007); parallel read-only execution.
