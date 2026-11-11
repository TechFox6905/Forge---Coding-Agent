# Demo 02: File Creation and Targeted Editing

## Objective
Demonstrate Forge's ability to create a new file and make precise, targeted string replacement edits using `write` and `edit`.

## Setup
Start in an empty directory or temporary test directory.

## Execution Steps
1. Launch Forge:
   ```bash
   uv run forge
   ```
2. Enter the prompt:
   ```text
   Create a python script named math_utils.py containing an add(a, b) function and a subtract(a, b) function.
   ```
3. Approve the `write` permission request with `y`.
4. Enter the follow-up prompt:
   ```text
   Now edit math_utils.py to add type annotations (int, int) -> int to both functions and add docstrings.
   ```
5. Approve the `edit` permission request with `y`.

## Expected Behavior
- Forge calls `write` with `math_utils.py` and the initial code.
- On the follow-up turn, Forge reads the file or directly calls `edit` with exact `old_text` matching the existing file and `new_text` with annotations and docstrings.
- No unrelated code or whitespace is corrupted.

## Human Evaluation Rubric
- [ ] **Precision:** `edit` matched existing file content exactly without errors.
- [ ] **Code Quality:** Functions are properly typed and docstrings are informative.
- [ ] **Permissions:** Both write and edit calls required and respected human approval.

