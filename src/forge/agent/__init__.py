"""The Pydantic AI ReAct loop (LLM ⇄ tools).

ADR-001 §1-2: ``forge``'s agent is a Pydantic AI :class:`~pydantic_ai.Agent` on Gemini.
:mod:`forge.agent.factory` builds it; :mod:`forge.agent.loop` drives ``agent.iter()`` as
the harness :data:`~forge.harness.runner.TurnHandler`, streaming model nodes into the
canonical :mod:`forge.entities.events`. Chat-only in task 004 (no tools yet); tools + the
permission gate land in task 005+.
"""
