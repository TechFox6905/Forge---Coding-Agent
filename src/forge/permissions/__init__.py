"""Permissions: the ask/allow/deny policy around every tool call (ADR-0002 §3).

The **gate** (:mod:`forge.permissions.gate`) is the *policy* object — given a
:class:`~forge.entities.permissions.PermissionRequest` it returns a
:class:`~forge.entities.permissions.PermissionDecision` (``allow`` / ``ask`` / ``deny``).
v1 policy is *ask on every tool call*; the gate does not own the terminal UI — resolving an
``ask`` into the human's allow/deny verdict is the resolver's job (wired by the TUI).

:mod:`forge.permissions.types` holds the narrow :class:`~forge.permissions.types.PermissionMode`
seam (only ``ask`` in v1; M3 adds ``default/plan/edit/bypass``). The shared value objects
(``PermissionRequest`` / ``PermissionDecision``) live in :mod:`forge.entities.permissions`.
"""
