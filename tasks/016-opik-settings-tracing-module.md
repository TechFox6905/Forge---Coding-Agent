---
id: 016-opik-settings-tracing-module
feature: opik-observability
status: done
---

# Opik observability — settings, tracing module, initialization, dependency

Tags: `observability`, `opik`, `config`, `deps`
Depends on: None
Blocks: #017, #018, #019

## Scope

Implement the foundation for Opik observability (ADR-002): settings, one small observability module, the presence-based `init_tracing()` seam, the Logfire dependency, and test isolation.

No agent or REPL call sites are wired yet. The application must remain behaviorally unchanged until task 017 integrates the tracing seam.

- **Settings** — add an Observability: Opik block to Forge's existing settings module:

  - `opik_api_key: SecretStr = SecretStr("")` — presence-based activation.
  - `opik_workspace: str = "default"` — the `Comet-Workspace` OTLP header.
  - `opik_project_name: str = "forge"` — the `projectName` OTLP header.
  - `opik_url_override: str | None = None` — optional OTLP base URL override.

  Cloud base:
  `https://www.comet.com/opik/api/v1/private/otel`

  Self-hosted example:
  `http://localhost:5173/api/v1/private/otel`

  The exporter appends `/v1/traces`.

- **`.env.example`** — add a fully commented Opik configuration block documenting all four variables. Explain that tracing is enabled only when `OPIK_API_KEY` is provided. Copying the example file must not activate tracing accidentally.

- **Module** — create:

  - `src/forge/observability/__init__.py`
  - `src/forge/observability/tracing.py`

  Keep the module small and cohesive.

  Public API:

  - `init_tracing() -> bool`

    - Presence-based and idempotent.
    - When the API key is empty, return `False`.
    - Do not configure Logfire, initialize an exporter, emit spans, or mutate global `OTEL_-` environment variables when disabled.
    - When enabled:

      1. Resolve the OTLP base URL from settings.
      2. Construct `OTLPSpanExporter` with endpoint `<base>/v1/traces`.
      3. Configure the three headers: `Authorization`, `Comet-Workspace`, and `projectName`.
      4. Configure Logfire with `send_to_logfire=False` and a `BatchSpanProcessor`.
      5. Call `logfire.instrument_pydantic_ai()` globally.
      6. Emit one INFO log identifying the project and target kind (cloud or self-hosted).
      7. Return `True`.

    Use a module-level activation flag to prevent repeated process-global Logfire configuration.

  - `is_tracing_active() -> bool`

    - Return the current module activation state.

  - `root_span(name: str, -, thread_id: str | None = None)`

    - When active, return a Logfire span context manager.
    - When inactive, return `contextlib.nullcontext()`.

  - `record_output(span, output) -> None`

    - Record the final turn output on the manually created root span.
    - Must be safe when tracing is inactive.
    - Follow the root-span input/output mapping required by ADR-002.

  - `reset_tracing() -> None`

    - Reset module state for test isolation.
    - Do not assume resetting the module flag alone resets Logfire's process-global provider.

- **Dependency** — add `logfire` as the only new top-level runtime dependency.

  Do not add:

  - `opik`
  - `logfire[httpx]`
  - Separate OpenTelemetry exporter or SDK dependencies unless the resolver proves they are required.

  Update `uv.lock`.

- **Test isolation** — add an autouse `_no_opik_tracing` fixture to the appropriate test conftest. It must ensure ordinary tests run with an empty Opik API key.

  Tests that assert spans must explicitly activate tracing and isolate the Logfire provider using `logfire.testing`.

## Acceptance Criteria

- [x] All four settings fields exist with the specified defaults.
- [x] Settings initialization and reload produce no warnings under `filterwarnings=["error"]`.
- [x] `.env.example` documents all four variables and keeps the Opik block commented out.
- [x] No-key initialization returns `False` and does not configure Logfire.
- [x] No-key initialization does not mutate any `OTEL_-` environment variable.
- [x] `is_tracing_active()` returns `False` when disabled.
- [x] `root_span()` returns a no-op context manager when disabled.
- [x] Fake-key initialization configures the exporter and global Pydantic AI instrumentation.
- [x] Exporter endpoint and headers are constructed from settings.
- [x] Initialization is idempotent.
- [x] The activation log is emitted exactly once.
- [x] `record_output()` records root-span output correctly.
- [x] `reset_tracing()` supports hermetic test isolation.
- [x] Unit tests mirror the new observability module.
- [x] `uv.lock` is updated.
- [x] `make ci` passes without Opik credentials or network access.

## Out of scope

- Wiring tracing into the REPL or agent lifecycle (017).
- Root spans for individual turns.
- Documentation updates (018).
- Integration capstone and optional live smoke test (019).
- Evaluation datasets, experiments, and scoring.
