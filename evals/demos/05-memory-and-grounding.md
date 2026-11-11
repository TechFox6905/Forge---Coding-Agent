# Demo 05: Memory Obedience and Session Persistence

## Objective
Demonstrate that Forge obeys conventions defined in `AGENTS.md` and preserves high-level context across sessions in `MEMORY.md`.

## Setup
Create an `AGENTS.md` file in the working directory:
```markdown
# Project Rules
- All newly created python files must have docstrings written in French.
- Always use 4 spaces for indentation.
```

## Execution Steps
1. Launch Forge:
   ```bash
   uv run forge
   ```
2. Enter the prompt:
   ```text
   Create a small module greetings.py with a hello_world() function.
   ```
3. Approve the `write` tool call.
4. Inspect `greetings.py`.
5. Exit Forge with `/quit` or `Ctrl-D`.
6. Inspect `MEMORY.md` to observe the generated session summary.

## Expected Behavior
- Forge automatically discovers `AGENTS.md` and loads it into its system instructions.
- The generated `greetings.py` has French docstrings as mandated by the memory rule.
- Upon session exit, Forge appends a dated summary of the turn to `MEMORY.md`.

## Human Evaluation Rubric
- [ ] **Instruction Obedience:** The generated code strictly follows the rule declared in `AGENTS.md`.
- [ ] **Session Memory:** `MEMORY.md` records an accurate, concise one-line summary.
- [ ] **Persisted State:** Future sessions can load and resume from this context.

