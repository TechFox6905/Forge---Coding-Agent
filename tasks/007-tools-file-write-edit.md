---
id: 007-tools-file-write-edit
feature: m1-vanilla-agent
status: done
---

# Tools: file write + edit

## Scope
Mutating file tools (gated). `edit` uses exact-then-fuzzy matching validated against pi.

## Acceptance criteria
- [x] `write` creates/overwrites; gated before touching disk.
- [x] `edit` strips BOM + normalizes CRLF↔LF, matches exact (`indexOf`) then whitespace-normalized fuzzy, requires a UNIQUE match, restores original line endings on write.
- [x] 0 or >1 matches → model-readable `ModelRetry` ("not found" / "ambiguous, N matches" / "empty").
- [x] A denied write/edit leaves the file untouched.

## Out of scope
- Per-realpath mutation queue (unneeded under sequential M1; M3).
