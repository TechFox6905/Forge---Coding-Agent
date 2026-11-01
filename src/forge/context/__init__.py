"""Context engineering: the M1 append-only JSONL session log (ADR-001 §9).

This package owns conversation persistence. M1 ships the deliberately minimal piece — a
replayable JSONL session log per run (:mod:`forge.context.session_log`) that ``forge --resume``
seeds ``message_history`` from. SQLite-backed compaction and the conversation log proper arrive
in later milestones; the JSONL log is the seam they grow from.
"""

from __future__ import annotations

from forge.context.session_log import SessionLog, load, load_latest, resolve_session

__all__ = ["SessionLog", "load", "load_latest", "resolve_session"]
