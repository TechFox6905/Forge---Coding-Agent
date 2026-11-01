"""The permission gate: the ask/allow/deny **policy** object (ADR-001 §3).

:class:`PermissionGate` answers one question — given a
:class:`~forge.entities.permissions.PermissionRequest`, should the tool run? In v1 the
policy is *ask on every tool call*: :meth:`PermissionGate.check` always returns an ``ASK``
decision under :attr:`~forge.permissions.types.PermissionMode.ASK`, regardless of the
tool's ``read_only`` flag (the flag is recorded on the request for M3's read-only auto-allow
but ignored by the v1 decision).

The gate is **policy only** — it does *not* prompt the user or own the terminal UI. The loop
turns an ``ASK`` into the human's terminal allow/deny verdict via the resolver on
:class:`~forge.agent.deps.AgentDeps`. Keeping the gate a pure, synchronous policy object is
what lets M3 layer modes (``default/plan/edit/bypass``), read-only auto-allow, and persisted
rules on top of :meth:`check` without touching the loop or the TUI.
"""

from __future__ import annotations

import logging

from forge.entities.permissions import PermissionDecision, PermissionRequest
from forge.permissions.types import PermissionMode

logger = logging.getLogger(__name__)


class PermissionGate:
    """Decide allow/ask/deny for a tool call (ADR-001 §3); v1 always asks.

    Holds the active :class:`~forge.permissions.types.PermissionMode` (only ``ASK`` in v1).
    Stateless beyond that mode, so one instance is shared for a whole session.
    """

    def __init__(self, mode: PermissionMode = PermissionMode.ASK) -> None:
        self._mode = mode

    @property
    def mode(self) -> PermissionMode:
        """The mode the gate evaluates under (``ASK`` in v1)."""
        return self._mode

    def check(self, request: PermissionRequest) -> PermissionDecision:
        """Return the gate's verdict for ``request``.

        v1 policy: always ``ASK`` (route to the human). The tool's ``read_only`` flag is
        recorded on the request but does not change the v1 decision — read-only auto-allow
        arrives with the M3 modes.
        """
        logger.debug(
            "gate.check tool=%s read_only=%s mode=%s -> ask",
            request.tool_name,
            request.read_only,
            self._mode.value,
        )
        return PermissionDecision.ask(mode=self._mode)
