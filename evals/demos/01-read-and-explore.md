# Demo 01: File Reading and Codebase Exploration

## Objective
Demonstrate Forge's ability to inspect and explore unfamiliar code using its dedicated `read` tool rather than shelling out to `cat` or `head`.

## Setup
In your workspace or a test repository, ensure `pyproject.toml` exists.

## Execution Steps
1. Launch Forge:
   ```bash
   uv run forge
   ```
2. Enter the prompt:
   ```text
   Read pyproject.toml and summarize the project's dependencies and python version requirement.
   ```
3. When prompted by the permission gate to approve the `read` tool call, approve with `y`.

## Expected Behavior
- Forge requests permission to call `read` on `pyproject.toml`.
- Once approved, the numbered file contents are returned to the model.
- Forge streams a concise, accurate summary of dependencies and Python version requirement without hallucinating packages not present in the file.

## Human Evaluation Rubric
- [ ] **Tool Selection:** Selected `read` rather than `bash(cat pyproject.toml)`.
- [ ] **Approval Prompt:** Correctly paused for user approval before reading the file.
- [ ] **Accuracy:** All cited dependencies and Python version matches `pyproject.toml` exactly.

