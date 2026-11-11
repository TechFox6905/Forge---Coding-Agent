"""Application configuration via pydantic-settings.

Import the module-level ``settings`` singleton where you need configuration; never read
``os.environ`` deep in call sites. Every variable here is mirrored in ``.env.example``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Defaults are safe for tests, not production."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Inference: Gemini (see AGENTS.md). M2 adds OpenRouter / Modal behind a gateway. ---
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"  # config-driven; confirm the exact id at task 004

    # --- Logging ---
    log_level: str = "INFO"

    # --- Observability: Opik (ADR-002) ---
    # Presence-based tracing, like every prior optional surface (sandbox/runtime): set ``opik_api_key``
    # (the presence trigger + the OTLP ``Authorization`` header) and forge emits one Trace per turn
    # (REPL) / per run (``forge run``) — every LLM + tool call with tokens and (for priced models) cost.
    # Empty (the default) → ``observability.init_tracing()`` is a silent no-op and forge is
    # byte-identical (no spans, no network). Export is configured PROGRAMMATICALLY from these fields —
    # never via global ``OTEL_*`` env vars — so kitaru→zenml's own OpenTelemetry SDK is untouched
    # (ADR-002 §2). No readers yet: 017 wire the seam.
    opik_api_key: SecretStr = SecretStr("")
    opik_workspace: str = "default"  # the ``Comet-Workspace`` OTLP header
    opik_project_name: str = "forge"  # the ``projectName`` OTLP header (Opik groups traces by it)
    # The OTLP **base** URL. ``None`` → Comet cloud base
    # (``https://www.comet.com/opik/api/v1/private/otel``); set to a self-hosted Opik base, e.g.
    # ``http://localhost:5173/api/v1/private/otel``. The exporter appends ``/v1/traces``.
    opik_url_override: str | None = None

    # --- Evaluation suite (ADR-003) ---
    groq_api_key: SecretStr = SecretStr("")
    eval_judge_model: str = "groq/openai/gpt-oss-120b"
    eval_project_name: str = "forge-evals"

    # --- Tool execution / output truncation (tasks 006/008/010) ---
    bash_timeout_s: float = 120.0
    max_output_lines: int = 2000
    max_output_bytes: int = 50_000
    web_fetch_timeout_s: float = 30.0

    # --- Memory caps (task 012/013) ---
    memory_max_lines: int = 200
    memory_max_bytes: int = 25_000

    # --- Harness artifacts: everything forge writes lives under <cwd>/.forge (Fix 1). ---
    forge_dir: Path = Path(".forge")

    # --- Persistence: JSONL session log (task 014) ---
    sessions_dir: Path = Path(".forge/sessions")


settings = Settings()
