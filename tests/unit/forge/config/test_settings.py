from pathlib import Path

from forge.config import settings as singleton
from forge.config.settings import Settings

# Observability: Opik vars introduced by ADR-002 (task 016). Cleared in default tests so a
# developer's real environment cannot leak into the assertions.
_OPIK_ENV_VARS = (
    "OPIK_API_KEY",
    "OPIK_WORKSPACE",
    "OPIK_PROJECT_NAME",
    "OPIK_URL_OVERRIDE",
)


def test_defaults(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    s = Settings(_env_file=None)
    assert s.gemini_model == "gemini-3.5-flash-lite"
    assert s.max_output_lines == 2000
    assert s.max_output_bytes == 50_000
    assert s.memory_max_lines == 200
    assert s.memory_max_bytes == 25_000
    assert s.forge_dir == Path(".forge")
    assert s.sessions_dir == Path(".forge/sessions")
    assert s.gemini_api_key.get_secret_value() == ""


def test_reads_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret123")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    s = Settings(_env_file=None)
    assert s.gemini_api_key.get_secret_value() == "secret123"
    assert s.gemini_model == "gemini-2.5-pro"


def test_loads_values_from_a_dotenv_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=sk-from-dotenv\nGEMINI_MODEL=gemini-2.5-pro\n")
    s = Settings(_env_file=str(env))
    assert s.gemini_api_key.get_secret_value() == "sk-from-dotenv"
    assert s.gemini_model == "gemini-2.5-pro"


def test_process_env_var_overrides_dotenv(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=sk-from-dotenv\n")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-from-process-env")
    s = Settings(_env_file=str(env))
    assert s.gemini_api_key.get_secret_value() == "sk-from-process-env"


def test_secret_not_in_repr():
    s = Settings(_env_file=None, gemini_api_key="topsecret")
    assert "topsecret" not in repr(s)


def test_module_singleton_is_settings_instance():
    assert isinstance(singleton, Settings)


# --- Observability: Opik (ADR-002, task 016) --------------------------------------------------


def test_opik_defaults(monkeypatch):
    for var in _OPIK_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.opik_api_key.get_secret_value() == ""  # presence trigger — empty == tracing off
    assert s.opik_workspace == "default"
    assert s.opik_project_name == "forge"
    assert s.opik_url_override is None  # None == Comet cloud OTLP base


def test_reads_opik_vars_from_process_env(monkeypatch):
    monkeypatch.setenv("OPIK_API_KEY", "opik-secret-123")
    monkeypatch.setenv("OPIK_WORKSPACE", "my-workspace")
    monkeypatch.setenv("OPIK_PROJECT_NAME", "my-project")
    monkeypatch.setenv("OPIK_URL_OVERRIDE", "http://localhost:5173/api/v1/private/otel")
    s = Settings(_env_file=None)
    assert s.opik_api_key.get_secret_value() == "opik-secret-123"
    assert s.opik_workspace == "my-workspace"
    assert s.opik_project_name == "my-project"
    assert s.opik_url_override == "http://localhost:5173/api/v1/private/otel"


def test_loads_opik_vars_from_a_dotenv_file(tmp_path, monkeypatch):
    for var in _OPIK_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "OPIK_API_KEY=sk-opik-dotenv\n"
        "OPIK_WORKSPACE=ws-dotenv\n"
        "OPIK_PROJECT_NAME=proj-dotenv\n"
        "OPIK_URL_OVERRIDE=https://opik.example.com/api/v1/private/otel\n"
    )
    s = Settings(_env_file=str(env))
    assert s.opik_api_key.get_secret_value() == "sk-opik-dotenv"
    assert s.opik_workspace == "ws-dotenv"
    assert s.opik_project_name == "proj-dotenv"
    assert s.opik_url_override == "https://opik.example.com/api/v1/private/otel"


def test_opik_api_key_not_in_repr():
    s = Settings(_env_file=None, opik_api_key="topsecretopik")
    assert "topsecretopik" not in repr(s)


def test_env_example_lists_every_opik_var():
    """Drift guard: each Opik setting has a matching line in .env.example (AGENTS.md gate)."""
    env_example = (Path(__file__).parents[4] / ".env.example").read_text()
    for var in _OPIK_ENV_VARS:
        assert var in env_example, f"{var} missing from .env.example"


def test_copying_env_example_to_dotenv_does_not_activate_opik(monkeypatch):
    """A copied .env.example must NOT set a truthy OPIK_API_KEY (presence-based silent-no-op default).

    The Opik block ships fully commented out, so loading .env.example verbatim as the .env file leaves
    ``opik_api_key`` empty — tracing stays off. Guards the task-016 regression where an uncommented
    ``OPIK_API_KEY=changeme`` would make a copied .env try to trace against Comet with a bogus token.
    """
    for var in _OPIK_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    env_example = Path(__file__).parents[4] / ".env.example"
    s = Settings(_env_file=str(env_example))
    assert s.opik_api_key.get_secret_value() == ""
