import logging

import pytest

import forge.logging as dlog


@pytest.fixture
def _fresh_logger(monkeypatch):
    """Reset the init-once flag so each test configures logging from scratch.

    Tears down afterward: remove and close every root handler so a file handler this test opened
    does not leak an open file (or pollute the next test) — the suite runs with no console handler
    once Fix 3 lands, and a dangling FileHandler would keep writing into a tmp dir that is gone.
    """
    monkeypatch.setattr(dlog, "_INITIALIZED", False)
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()


def test_init_logger_sets_root_level(monkeypatch, _fresh_logger, tmp_path):
    monkeypatch.setenv("FORGE_LOG_FILE", str(tmp_path / "forge.log"))
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    dlog.init_logger()
    assert logging.getLogger().level == logging.WARNING


def test_explicit_level_overrides_env(monkeypatch, _fresh_logger, tmp_path):
    monkeypatch.setenv("FORGE_LOG_FILE", str(tmp_path / "forge.log"))
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    dlog.init_logger("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_init_logger_is_idempotent(monkeypatch, _fresh_logger, tmp_path):
    monkeypatch.setenv("FORGE_LOG_FILE", str(tmp_path / "forge.log"))
    dlog.init_logger("INFO")
    before = len(logging.getLogger().handlers)
    dlog.init_logger("INFO")  # second call is a no-op
    assert len(logging.getLogger().handlers) == before


def test_init_logger_installs_no_console_handler(monkeypatch, _fresh_logger, tmp_path):
    # Fix 3: logs go to a file, OFF the terminal — no StreamHandler/RichHandler on root.
    from rich.logging import RichHandler

    monkeypatch.setenv("FORGE_LOG_FILE", str(tmp_path / "forge.log"))
    dlog.init_logger("INFO")

    handlers = logging.getLogger().handlers
    assert not any(isinstance(h, RichHandler) for h in handlers)
    # A FileHandler is a StreamHandler subclass; a *bare* StreamHandler (console) must be absent.
    assert not any(type(h) is logging.StreamHandler for h in handlers)


def test_init_logger_writes_to_the_configured_file(monkeypatch, _fresh_logger, tmp_path):
    # Fix 3: INFO+ lands in <FORGE_LOG_FILE>, creating the parent dir as needed.
    log_file = tmp_path / "logs" / "forge.log"
    monkeypatch.setenv("FORGE_LOG_FILE", str(log_file))
    dlog.init_logger("INFO")

    logging.getLogger("forge.test").info("hello-from-the-file-logger")

    assert log_file.is_file()
    assert "hello-from-the-file-logger" in log_file.read_text(encoding="utf-8")


def test_init_logger_creates_the_logs_dir_lazily(monkeypatch, _fresh_logger, tmp_path):
    # delay=True: the file is opened on first emit, but the parent dir is ensured up-front so the
    # first write never explodes.
    log_file = tmp_path / "nested" / "logs" / "forge.log"
    monkeypatch.setenv("FORGE_LOG_FILE", str(log_file))
    dlog.init_logger("INFO")

    assert log_file.parent.is_dir()


def test_empty_forge_log_file_disables_file_logging(monkeypatch, _fresh_logger, tmp_path):
    # Fix 3: FORGE_LOG_FILE="" disables file logging via a NullHandler (no file ever created).
    monkeypatch.setenv("FORGE_LOG_FILE", "")
    monkeypatch.chdir(tmp_path)
    dlog.init_logger("INFO")

    logging.getLogger("forge.test").info("must-not-be-written")

    handlers = logging.getLogger().handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)
    assert not any(isinstance(h, logging.FileHandler) for h in handlers)
    # No .forge/logs dir is created under the cwd when logging is disabled.
    assert not (tmp_path / ".forge" / "logs").exists()


def test_default_log_path_is_under_cwd_forge_logs(monkeypatch, _fresh_logger, tmp_path):
    # With no FORGE_LOG_FILE override, the default is <cwd>/.forge/logs/forge.log.
    monkeypatch.delenv("FORGE_LOG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    dlog.init_logger("INFO")

    logging.getLogger("forge.test").info("default-path-line")

    default_file = tmp_path / ".forge" / "logs" / "forge.log"
    assert default_file.is_file()
    assert "default-path-line" in default_file.read_text(encoding="utf-8")
