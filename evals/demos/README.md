# Forge Human-Judged Demo Scenarios (ADR-003 §2)

This directory contains curated showcase demo scenarios for Forge.
Unlike the automated benchmark (which evaluates whether code passes hidden oracles) and regression probes (which evaluate exact tool selection and behavioral metrics), **demos are human-judged showcase walkthroughs**.

They demonstrate that Forge impresses real developers across key agentic workflows:
1. **[01-read-and-explore.md](01-read-and-explore.md)**: File reading, inspection, and codebase exploration.
2. **[02-create-and-edit.md](02-create-and-edit.md)**: File creation and targeted string-replacement editing.
3. **[03-permissions-approval-and-denial.md](03-permissions-approval-and-denial.md)**: Ask-on-every-tool permission gate, human-in-the-loop approvals, and graceful handling of denied requests.
4. **[04-task-planning-and-execution.md](04-task-planning-and-execution.md)**: Task checklist management (`tasks` tool) across multi-stage work.
5. **[05-memory-and-grounding.md](05-memory-and-grounding.md)**: Instruction loading from `AGENTS.md` and session memory write-back to `MEMORY.md`.
6. **[06-multi-step-workflow.md](06-multi-step-workflow.md)**: End-to-end coding workflow: test diagnosing, editing code, re-running test suite with `bash`.

---

## How to Run a Demo

1. Ensure `GEMINI_API_KEY` is set in your environment:
   ```bash
   export GEMINI_API_KEY=...
   ```
2. Start Forge in your workspace or a temporary directory:
   ```bash
   uv run forge
   ```
3. Follow the prompt instructions in each demo document and observe Forge's streamed reasoning, tool call requests, and output.
4. Grade the result according to the human evaluation rubric in each file.

