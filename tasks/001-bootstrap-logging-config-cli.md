---
id: 001-bootstrap-logging-config-cli
feature: m1-vanilla-agent
status: done
---

# Bootstrap: logging, settings, CLI, entities

## Scope
Foundational package wiring: structured logging, the pydantic-settings singleton, the `forge` Click entrypoint, and the shared-entities package marker.

## Acceptance criteria
- [x] `logging.py` exposes `init_logger()`, called at module level in `cli.py` before any other project import.
- [x] `config/settings.py` defines `Settings` + a module-level `settings` singleton; reads `GEMINI_API_KEY`, `gemini_model`, output/memory caps, `sessions_dir` from env/`.env`.
- [x] `forge` CLI launches and exits cleanly (`uv run forge`), accepts `--resume [SESSION]`.
- [x] New env vars mirrored in `.env.example`.
- [x] `make pre-commit` green (ruff format + lint + unit tests).

## Out of scope
- The interactive REPL / TUI (task 002) and any agent behaviour. The CLI is a bootstrap stub.


