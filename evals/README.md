# Forge Evaluation Suite (ADR-003)

This is *about* the agent, not part of it — this `evals/` package is located outside `src/forge/` and never ships in the production wheel (ADR-003 §1).

It implements the four evaluation tracks defined in ADR-003:
1. **[Demo Scenarios](demos/README.md)** — human-judged showcase walkthroughs (`evals/demos/`).
2. **Outcome Benchmark** — 20 coding tasks graded against hidden oracles (`evals/benchmark/tasks/`).
3. **Behavioral Regression Suite** — 20 behavioral probes testing tool discipline, permissions, and grounding (`evals/regression/cases/`).
4. **Online Evaluation** — automated rules and scripted thread-level evaluation over live REPL sessions (`evals/harness/online.py`).

---

## Quick Start & Prerequisites

### Required Environment Variables

Evaluation tracks require API keys configured in `.env` or your shell environment:

```bash
# Agent model inference
export GEMINI_API_KEY="AIzaSy..."

# LLM-as-a-Judge evaluations via LiteLLM (ADR-003 §7)
export GROQ_API_KEY="gsk_..."

# Observability and dataset tracking (ADR-002, ADR-003)
export OPIK_API_KEY="opik_..."

# Optional overrides:
export EVAL_PROJECT_NAME="forge-evals"          # default: forge-evals
export EVAL_JUDGE_MODEL="groq/openai/gpt-oss-120b" # default
```

Live evaluation commands preflight these keys with `python -m evals.harness.keys`. If any key is missing, they exit cleanly with an informative message.

---

## 1. Outcome Benchmark (`evals/benchmark/`)

A benchmark task asks: *"Did the agent get the job done?"*

Each task lives under `evals/benchmark/tasks/<NNN>-<slug>/` with:
- `task.yaml`: Prompt, max steps, difficulty, and optional judge criteria.
- `setup/`: Seed files copied into a fresh temporary workspace.
- `verify/verify.sh`: Hidden grading oracle executed ONLY after the agent finishes.
- `solution/`: Committed gold overlay used by oracle sanity tests.

### Running the Benchmark

```bash
# Run the full 20-task benchmark:
make eval-benchmark
# or directly:
uv run python -m evals benchmark

# Run a single task:
uv run python -m evals benchmark --task 001-find-and-replace

# Run by difficulty tier (easy, medium, hard):
uv run python -m evals benchmark --difficulty easy

# Run repeated trials (Opik trial_count) for reliability aggregates:
uv run python -m evals benchmark --trials 3
```

Aggregates calculated:
- **pass@1**: Average single-trial success rate.
- **pass@k**: Fraction of tasks passed in at least one trial.
- **pass^k**: Fraction of tasks passed in every trial (reliability).
- **flakiness**: Fraction of tasks with mixed results across trials.
- **cost / tokens**: Normalized cost and tokens per successful task.

---

## 2. Behavioral Regression Probes (`evals/regression/`)

A regression probe asks: *"Did the agent work the RIGHT way?"*

Probes test specific agentic harness behaviors:
- Tool selection: `read` vs `cat`, `grep` vs `bash`, `edit` precision.
- Gating: Permission approvals, denial respect, destructive operation caution.
- Memory: Obedience to conventions in `AGENTS.md`.
- Output contracts: Valid JSON formatting, grounded answers without hallucinations.

### Running the Regression Suite

```bash
# Run the regression gate (pytest pre-merge ritual):
make eval-regression
# or directly:
uv run pytest evals/regression/test_thresholds.py

# Run regression probes through the CLI:
uv run python -m evals regression

# Run a single probe:
uv run python -m evals regression --probe 01-smoke-read-tool
```

### Thresholds & Baseline Comparison
- **Absolute Gate**: Tool-discipline metrics must clear ≥ 0.8; subjective LLM judges must clear ≥ 0.7.
- **Baseline Comparison**: Diffs per-metric means against the latest scored experiment with tolerance to warn on regressions.

---

## 3. Online Evaluation (`evals/harness/online.py`)

Grades traces and threads Forge already emitted during real REPL sessions in `settings.opik_project_name` (`forge`):

```bash
# Score all live threads in the project:
uv run python -m evals online

# Scope to recent threads with an OQL filter:
uv run python -m evals online --filter 'start_time > "2026-07-01T00:00:00Z"'
```

---

## 4. Dataset Synchronization

Upsert benchmark tasks and regression probes into Opik datasets (`forge-benchmark-v1` and `forge-regression-v1`):

```bash
uv run python -m evals sync
```

---

## 5. Offline Testing & CI

All unit tests for the eval harness live under `tests/unit/evals/` and run **offline without API keys or network access**:

```bash
# Run all harness unit tests:
uv run pytest tests/unit/evals -v

# Run the full CI gate (eval-free):
make ci
```
