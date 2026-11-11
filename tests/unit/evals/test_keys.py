"""Unit tests for :mod:`evals.harness.keys` (ADR-003 §9; task 020)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from evals.harness.keys import eval_keys_missing, main
from forge.config.settings import settings


def test_eval_keys_missing_when_all_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """When all 3 keys are present, eval_keys_missing() returns an empty list."""
    monkeypatch.setattr(settings, "opik_api_key", SecretStr("opik-test"))
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("gemini-test"))
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("groq-test"))

    assert eval_keys_missing() == []
    assert main() == 0


def test_eval_keys_missing_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """When keys are empty, eval_keys_missing() reports them and main exits 1."""
    monkeypatch.setattr(settings, "opik_api_key", SecretStr(""))
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr(""))
    monkeypatch.setattr(settings, "groq_api_key", SecretStr(""))
    monkeypatch.delenv("OPIK_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    missing = eval_keys_missing()
    assert "OPIK_API_KEY" in missing
    assert "GEMINI_API_KEY" in missing
    assert "GROQ_API_KEY" in missing
    assert main() == 1
