"""Shared pytest fixtures. Mirror src/ 1:1 under tests/unit and tests/integration."""

import os

# Disable file logging for the whole suite BEFORE any forge import (Fix 3). ``init_logger`` runs
# at import time in the ``forge.cli`` entrypoint; an empty ``FORGE_LOG_FILE`` installs a
# NullHandler so the suite never creates ``.forge/logs/`` in the repo. The individual
# ``test_logging`` tests set their own value via ``monkeypatch.setenv`` (which wins per-test).
os.environ["FORGE_LOG_FILE"] = ""

import pytest
from pydantic import SecretStr


@pytest.fixture(autouse=True)
def _no_real_provider_key(monkeypatch):
    """Hermeticity guard — no test may reach a real LLM provider.

    ``forge.config.settings.settings`` is built at import time and may have loaded a real
    ``GEMINI_API_KEY`` from a developer's local ``.env``. Without scrubbing it, any test that
    drives the real :func:`forge.tui.app.run_app` would, on exit, run the memory write-back
    (:func:`forge.memory.extract.extract_on_exit` → a *live* Gemini call) — leaking sockets and
    writing the repo's ``MEMORY.md``. CI has no key so it never hit this; a developer with a key
    did. We delete the env var and blank the singleton's key so that path no-ops everywhere.

    Tests that need the agent to *build* inject their own dummy key in a module-local autouse
    fixture (which runs after this conftest one, so it wins); tests that exercise the summarizer
    pass an explicit stub ``Model``. Settings instances built with an explicit ``_env_file`` are
    unaffected (they don't touch this singleton).
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from forge.config.settings import settings

    monkeypatch.setattr(settings, "gemini_api_key", SecretStr(""), raising=False)


@pytest.fixture(autouse=True)
def _no_opik_tracing(monkeypatch):
    """Hermeticity guard — no test may configure real Opik export (ADR-002 §7, task 016).

    ``forge.config.settings.settings`` is built at import time and may have loaded a real
    ``OPIK_API_KEY`` from a developer's local ``.env``. Once :func:`forge.observability.init_tracing`
    is wired into ``run_app`` , that key would make the suite configure
    a live OTLP exporter to Comet on the first turn/run — a real network side effect. Mirroring
    :func:`_no_real_provider_key`, we delete the env var and blank the singleton's key so
    ``init_tracing()`` no-ops everywhere.

    Span-asserting tracing tests opt in with their own fake key + ``logfire.testing``'s in-memory
    exporter (which wins, running after this conftest fixture) and reset the module flag via
    ``reset_tracing()`` themselves. Kept separate from the settings-block tests, which build explicit
    ``Settings(_env_file=…)`` objects untouched by this singleton blanking.
    """
    monkeypatch.delenv("OPIK_API_KEY", raising=False)

    from forge.config.settings import settings

    monkeypatch.setattr(settings, "opik_api_key", SecretStr(""), raising=False)
