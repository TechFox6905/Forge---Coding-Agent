"""Application configuration via pydantic-settings.

Import the module-level ``settings`` singleton where you need configuration; never read
``os.environ`` deep in call sites. Every variable here is mirrored in ``.env.example``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Defaults are safe for tests, not production."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Inference: Gemini (see AGENTS.md). M2 adds OpenRouter / Modal behind a gateway. ---
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"  # config-driven; confirm the exact id at task 004

    # --- Logging ---
    log_level: str = "INFO"
    # Log file path (Fix 3). Logs go to a file, off the terminal; default <cwd>/.forge/logs/
    # forge.log. Empty string disables file logging. Read from env ``FORGE_LOG_FILE``. NB:
    # ``logging.init_logger`` reads ``FORGE_LOG_FILE`` from the environment directly (it must
    # configure logging before importing this settings module), so this field exists for
    # documentation / a single declared surface, not as its reader.
    log_file: str = Field(
        default=str(Path(".forge") / "logs" / "forge.log"), alias="FORGE_LOG_FILE"
    )

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
