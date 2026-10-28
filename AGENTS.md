# forge

**forge** is a terminal **coding agent** ("agentic harness") built from scratch, step by step, as an educational open-source course. It is a single Python package, `forge`, exposing a TUI you run in your terminal: a Pydantic AI ReAct loop driving file/bash/web tools, with Gemini inference, ask-on-every-tool permissions, deferred tool execution, mid-turn steering, memory management, and replayable session logs.
Standalone single-package Python (`cli-tool-python` shape); the TUI is a module inside the package (`prompt_toolkit` input + `Rich` output), not a separate service.

# Key Components

Single package — one bullet for the package, then the internal module map under [Project Structure].

* **`forge`** — `src/forge/`: the whole coding agent. Python 3.12+, `cli-tool-python` shape (Click entrypoint launching the TUI).

  Conventions: async I/O for network operations, sync for CPU-bound operations; infrastructure imported directly (no premature interfaces); shared models in `entities/`, narrow types in `<module>/types.py`; every entrypoint calls `init_logger()` at module level before any project import.

# Project Structure

The implemented M1 architecture.

`tests/` mirrors `src/` 1:1.

```
.
├── AGENTS.md / CLAUDE.md          # this memory file (+ Claude Code import)
├── pyproject.toml                 # uv + hatchling; deps grow per step
├── Makefile                       # install / test / lint / format / pre-commit / build / ci
├── .pre-commit-config.yaml        # format + lint (commit) · unit tests (push)
├── .env.example                   # config & secrets surface
├── docs/
│   ├── adr/                       # Architecture Decision Records (Nygard)
│   └── glossary.md                # ubiquitous language
├── tasks/                         # file-based tracker — one md per task
├── tests/{unit,integration}/      # unit mirrors src/ 1:1; integration touches real infra
└── src/forge/
    ├── __init__.py
    ├── logging.py                 # init_logger() — module-level in every entrypoint
    ├── cli.py                     # Click entrypoint → launches the TUI        [bootstrap]
    ├── config/settings.py         # pydantic-settings; module-level `settings` singleton
    ├── entities/                  # shared models: Message, Conversation, ToolCall, Task…
    ├── tui/                       # input: prompt_toolkit · output: Rich (answers via SSE)
    ├── harness/                   # message Queue + Priority Gate around the loop
    ├── agent/                     # Pydantic-AI ReAct loop (LLM ⇄ Tools)
  
    ├── tools/                     # file I/O, Bash, web, tasks, MCP factory, skill dispatcher, LSP, AskUser
    ├── permissions/               # allow/ask/deny · modes (default/plan/edit/bypass) · settings.json
    ├── context/                   # context engineering: compaction + conversation log (SQLite)
    ├── memory/                    # AGENTS.md / MEMORY.md loading
    └── observability/             # Opik tracing
```

**Scripts & entrypoints.** Operator scripts in `scripts/`; CLI entrypoint declared in `pyproject.toml` `[project.scripts]` (`forge = "forge.cli:cli"`).

**Every entrypoint module calls `init_logger()` at module level before any project import.**

# Tech Stack

Single Python toolchain — `uv`, `ruff`, `pytest`.

**Python 3.12+.**

| Layer               | Choice                              | Notes                                                                            |
| ------------------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| Package/deps        | `uv` + `hatchling`                  | `uv.lock` committed; `uv sync` is the installer.                                 |
| Lint/format         | `ruff`                              | One configuration block in `pyproject.toml`; format + check are separate passes. |
| Test                | `pytest` + `asyncio` + `mock`       | `tests/` mirrors `src/`; `filterwarnings=["error"]`.                             |
| CLI / TUI           | `click` · `prompt_toolkit` · `rich` | Click wrapper is thin; logic stays in the application layer.                     |
| Agent loop          | `pydantic-ai`                       | ReAct loop using `agent.iter()` and deferred tool execution.                     |
| Inference           | Gemini                              | Configured through Pydantic AI's `google-gla:` provider.                         |
| Memory              | `AGENTS.md` + `MEMORY.md`           | Instruction loading and minimal session-summary write-back.                      |
| Session persistence | JSONL                               | Append-only session log with Pydantic AI message serialization.                  |

Per-step dependencies are managed through `uv add`.

# Access Documentation

Use the `context7` MCP server (when connected) to look up authoritative usage for any tech-stack item or external service; fall back to web search otherwise.

**Reference docs (`llms.txt` — fetch on demand).** Each link below is an index of documentation pages. Fetch the index first, then fetch only the specific pages you need. Do not pull entire documentation collections into context unless a task requires them.

* **Pydantic AI:** https://pydantic.dev/docs/ai/llms.txt
* **Gemini:** https://ai.google.dev/gemini-api/docs

# Running commands

All core verbs run at the repo root via the `Makefile`, wrapping `uv`:

| Verb                                    | What it does                                    |
| --------------------------------------- | ----------------------------------------------- |
| `make install`                          | `uv sync` + install git hooks.                  |
| `make test`                             | Full suite (`uv run pytest`).                   |
| `make unit-tests`                       | Unit tests.                                     |
| `make integration-tests`                | Integration tests.                              |
| `make lint-check` / `make lint-fix`     | `ruff check` (assert vs write).                 |
| `make format-check` / `make format-fix` | `ruff format` (assert vs write).                |
| `make pre-commit`                       | Format-check + lint-check + unit-tests.         |
| `make build`                            | `uv build` → wheel + sdist.                     |
| `make ci`                               | Lock check + format-check + lint-check + tests. |
| `make help`                             | Curated target list.                            |

Commands not wrapped by `make` — use the runner directly: `uv run <cmd>`, `uvx <one-shot-tool>`.

**Manual QA order:** `format-fix → lint-fix → format-check → lint-check → pre-commit → unit-tests`.

**Dependencies & env vars.** Add runtime dependencies with `uv add <pkg>`; dev tools with `uv add --group dev <pkg>`.

New environment variables must be added to `.env.example` and `config/settings.py`. Never read `os.environ` deep in call sites.

# Infrastructure & external services

Access infrastructure through documented CLI commands and SDKs.

* **Git / GitHub:** `git`; `gh` for PRs, issues, and Actions logs.

* **Gemini** — primary LLM provider through Pydantic AI's `google-gla:` configuration. API credentials are read from `GEMINI_API_KEY`. Model selection is configurable through `settings.gemini_model`.

# Key Principles You Will Respect All Over Your Work

* Always prioritize removing unnecessary instructions over adding more.

* Whenever you add a new rule to memory (e.g. `AGENTS.md`), support it with a concise explanation and good/bad examples where useful.

* **Build it step by step.** This is a teaching codebase — favour the simplest thing that works and is readable over clever or speculative implementations. One concept per step; no abstraction without a second concrete caller.

* **Infrastructure is imported, not abstracted.** Use Pydantic AI, Gemini, Logfire, OpenTelemetry, and other existing infrastructure directly. Introduce an interface only when a genuine second implementation requires it.

* **Permissions are ask-on-every-tool-call in v1.** Every tool call requires approval, including read-only tools. Do not introduce automatic approval or permission modes unless an accepted ADR explicitly changes this policy.

* **Deferred execution is the HITL mechanism.** Tool approvals and AskUser interactions use Pydantic AI's `DeferredToolRequests` and `DeferredToolResults`. Preserve the multi-leg execution model.

* **Steering and follow-up are different interactions.** Steering is injected at model-request boundaries. Follow-up messages are processed only when the agent would otherwise stop. Do not merge these queues.

* **Abort is cooperative.** `Esc` sets an abort flag. Execution stops at the next boundary; do not introduce hard cancellation into the current architecture.

* **Datetimes are timezone-aware (UTC).** Reject naive `datetime` values at boundaries. Type-annotate everything, including `-> None`.

* **Library code never uses `print()`.** Use the logger. User-facing CLI output goes through `click.echo` or `rich`.

* **Keep tests hermetic.** Model interactions in CI must use `TestModel` or `FunctionModel`. Tests must not require API keys or network access.

# Developing New Features & Bug Fixes

Follow the existing task-driven development workflow.

Before implementing a feature or changing architecture:

1. Read the relevant ADRs in `docs/adr/`.
2. Inspect the existing implementation and tests.
3. Check whether the requested change conflicts with an accepted architectural decision.
4. Update the relevant task documentation when applicable.
5. Implement the smallest change that satisfies the requirement.
6. Add or update tests.
7. Run the relevant quality gates before committing.

**Architecture is governed by accepted ADRs.** Do not independently introduce new architectural patterns, dependencies, abstractions, or infrastructure.

| Role              | Responsibility                                                        |
| ----------------- | --------------------------------------------------------------------- |
| Architect         | Defines architecture, ADRs, and implementation boundaries.            |
| Software Engineer | Implements code and tests while preserving accepted decisions.        |
| Tester            | Verifies behaviour through unit, integration, and adversarial tests.  |
| Reviewer          | Reviews correctness, simplicity, tests, standards, and documentation. |

Engineering discipline:

* TDD-first where practical.
* Regression-test-first for bugs.
* Keep changes scoped to the relevant task.
* Run integration tests before declaring an architectural feature complete.
* Do not modify unrelated code or documentation.

**Tracker:** `TRACKER_MODE: file`. Tasks are maintained under `tasks/`. Follow the existing task format and status conventions.

Project-specific invariants:

* **Deferred execution is the approval boundary.** Do not execute a deferred tool call before its corresponding approval result is supplied.

* **The single-flight lock covers the complete turn.** It must remain active across every `agent.iter()` leg, deferred pause, and resume.

* **Steering is boundary-based.** Never interrupt an active model stream or tool execution to inject steering.

* **Tool execution is sequential in v1.** Do not introduce parallel tool execution without an accepted ADR.

* **All tool calls require approval.** The `PermissionGate` policy must remain consistent with ADR-001.

* **Session persistence is append-only JSONL.** Preserve the existing session serialization and replay behaviour.

* **Memory is intentionally minimal.** Preserve the existing AGENTS.md/MEMORY.md loading and summary write-back approach. Do not introduce compaction or a different memory architecture without an ADR.

* **One trace represents one complete REPL turn.** The root `chat_turn` span must cover the entire lifecycle, including deferred approval and resume.

* **Use settings-driven telemetry configuration.** Do not configure global `OTEL_*` environment variables or introduce additional tracing providers without an ADR.

* **Preserve test isolation.** Ordinary tests must not export real telemetry. Use `logfire.testing` and in-memory exporters for instrumentation tests.

# Testing E2E

The automated proof that the M1 stack hangs together is the capstone integration test:

[`tests/integration/test_milestone1_capstone.py`](tests/integration/test_milestone1_capstone.py).

It drives a six-step conversation through the real `build_agent()` + `Runner` + `render_event` + session log + memory write-back, swapping only the network boundary (`FunctionModel` for the model and `httpx.MockTransport` for the web tool).

Run it with `make integration-tests` (or the full gate, `make ci`).

It requires no API key and makes no network call.

What follows is the manual E2E pass against real Gemini.

**Launch.** One environment variable, no external service to start first:

```bash
export GEMINI_API_KEY=...
uv run forge
```

A bare `uv run forge` without `GEMINI_API_KEY` must print one friendly line on stderr:

`forge: set GEMINI_API_KEY in your environment or .env to start (see .env.example).`

It must exit non-zero, not produce a traceback.

For each surface below: the thing to type, and what working looks like.

| Surface         | Type this                                                                                           | Working looks like                                                                                                                                                  |
| --------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Plain chat      | `what can you do?`                                                                                  | The answer streams above the prompt.                                                                                                                                |
| Read            | `read pyproject.toml`                                                                               | Permission prompt appears; approve with `y` to display numbered file contents.                                                                                      |
| Write (approve) | `create hello.txt containing hi`                                                                    | Permission prompt appears; approve with `y`; file is created.                                                                                                       |
| Write (deny)    | Repeat the write and answer `n`.                                                                    | File is not created; the model receives the denial result.                                                                                                          |
| Bash            | `run the tests with make unit-tests`                                                                | Permission prompt appears; command output is displayed and bounded by configured limits.                                                                            |
| Todo checklist  | `make a 3-step plan to add a CLI flag`                                                              | Tasks panel renders and updates as the model changes task statuses.                                                                                                 |
| Web fetch       | `fetch https://example.com and summarize it`                                                        | Permission prompt appears; HTML is converted to Markdown and summarized.                                                                                            |
| AskUser         | `deploy my app`                                                                                     | The agent asks a clarifying question and resumes after receiving the answer.                                                                                        |

**Mid-turn interaction** (ADR-001 §4-5):

* **Steer** — start a long turn, type a line, and press plain `Enter`. The message is injected at the next model-request boundary.
* **Follow-up** — press `Alt+Enter`. The message is queued and processed only when the current turn would otherwise stop.
* **Abort** — press `Esc`. The turn stops at the next execution boundary, preserves completed work, and returns the REPL to idle.

**Persistence + memory across sessions:**

* `forge --resume` replays the latest session.
* `forge --resume <session-id>` replays the specified session.
* Session logs are stored in `.forge/sessions/` as append-only JSONL files.
* On quit (`/quit` or `Ctrl-D`), one Gemini call appends a dated one-line summary to `MEMORY.md`.
* On the next launch, the memory content is loaded into the agent's instructions.

# Documentation Conventions

* **ADRs** at [`docs/adr/`](docs/adr/) — `NNN-kebab-title.md`, Nygard template (Status / Context / Decision / Consequences).

  Every non-obvious architectural decision must be documented in an ADR before introducing architectural changes.