# Demo 04: Task Planning and Checklist Execution

## Objective
Demonstrate Forge's structured task planning and progress tracking using the `tasks` tool.

## Setup
Start in a clean workspace directory.

## Execution Steps
1. Launch Forge:
   ```bash
   uv run forge
   ```
2. Enter the prompt:
   ```text
   Create a 3-step checklist to set up a new Python CLI project with Click and Rich, then execute the first step.
   ```
3. Approve each requested tool call.

## Expected Behavior
- Forge calls `tasks` to create initial pending tasks (e.g. 1. Initialize repository & dependencies, 2. Create CLI entrypoint, 3. Add Rich formatting).
- Forge's TUI updates the task panel in real time.
- Forge begins executing step 1, updating its status to `in_progress` and then `completed`.

## Human Evaluation Rubric
- [ ] **Planning:** High-quality, logically ordered task breakdown.
- [ ] **State Updates:** Tasks move from pending to in_progress to completed appropriately.
- [ ] **Visibility:** Progress is clearly reported to the user.

