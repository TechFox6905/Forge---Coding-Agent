"""Shared fixture builders the regression probes seed a fresh Workspace with (ADR-003 §6).

Each builder is a small, offline, reusable seed a probe's ``fixture`` or ``context`` composes:

* :func:`serve_page` — a stdlib ``http.server`` serving one known page on localhost, as a context
  manager a probe enters around the run (the web-fetch probe).

They are re-exported here so a probe writes ``from evals.regression.fixtures import serve_page``.
"""

from __future__ import annotations

from evals.regression.fixtures.web import serve_page

__all__ = [
    "serve_page",
]
