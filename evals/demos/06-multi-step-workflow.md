# Demo 06: Multi-Step Debugging and Tool Workflow

## Objective
Demonstrate an end-to-end coding workflow: running a failing test, diagnosing the error, editing the implementation, and verifying the fix with a green test run.

## Setup
In a test directory, create `calculator.py`:
```python
def divide(a: int, b: int) -> float:
    # Bug: ignores division by zero
    return a / b
```

And `test_calculator.py`:
```python
import pytest
from calculator import divide


def test_divide():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)
```

## Execution Steps
1. Launch Forge:
   ```bash
   uv run forge
   ```
2. Enter the prompt:
   ```text
   Run pytest test_calculator.py. If there are failures, inspect calculator.py, fix the bug so the test passes, and re-run pytest to verify.
   ```
3. Approve each tool call (`bash`, `read`, `edit`, `bash`).

## Expected Behavior
- Forge runs `pytest test_calculator.py` using `bash` and captures the test failure.
- Forge uses `read` or `edit` to inspect and update `calculator.py` to raise `ValueError("Cannot divide by zero")` when `b == 0`.
- Forge executes `pytest test_calculator.py` again using `bash` and verifies that all tests pass.
- Forge concludes with a clear explanation of what was broken and how it was resolved.

## Human Evaluation Rubric
- [ ] **Autonomous Loop:** Correct sequence of test -> diagnose -> edit -> verify.
- [ ] **Minimal Mutation:** Fixed only the buggy code path without unnecessary refactoring.
- [ ] **Verification Evidence:** Confirmed green test results before reporting success.
