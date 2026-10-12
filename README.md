# Forge

**Forge** is a terminal-based AI coding agent built around an agentic harness. It is designed to combine LLM-driven reasoning with tools for file operations, shell execution, web access, and Model Context Protocol (MCP) integrations.

The project aims to bring together agent orchestration, pluggable inference providers, sandboxed execution, and observability in a single Python application.

## Architecture

Forge is organized as a single Python package, with application code under `src/forge/`. Each module is responsible for a distinct part of the system.

The intended architecture includes:

* **Agent orchestration:** A Pydantic AI-powered ReAct loop for reasoning and tool execution.
* **Terminal interface:** An interactive TUI built with `prompt_toolkit` and `Rich`.
* **Tool integration:** File operations, shell commands, web access, and MCP tools.
* **Inference:** Support for Gemini, OpenRouter, and Modal-hosted models.
* **Sandboxing:** Local and remote environments for executing commands.
* **Observability:** Opik-based tracing and evaluation.
* **Durability:** A Kitaru-based runtime for durable execution and workflow management.

These components will be implemented incrementally as the project develops.

## Tech Stack

| Component                         | Technology                  |
| --------------------------------- | --------------------------- |
| Language                          | Python 3.12+                |
| Package management                | uv                          |
| Build system                      | Hatchling                   |
| CLI                               | Click                       |
| Terminal UI                       | prompt_toolkit, Rich        |
| Data validation and configuration | Pydantic, pydantic-settings |
| Linting and formatting            | Ruff                        |
| Testing                           | pytest, pytest-asyncio      |
| Agent framework                   | Pydantic AI                 |

Additional integrations will be introduced as their corresponding components are implemented.

## Getting Started

### Prerequisites

* Python 3.12 or later
* [uv](https://docs.astral.sh/uv/)

### Installation

Clone the repository and navigate to the project directory.

Install the project dependencies and development tools:

```bash
make install
```

### Development

Run the test suite:

```bash
make test
```

Check code formatting:

```bash
make format-check
```

Run lint checks:

```bash
make lint-check
```

Run the complete CI quality gate:

```bash
make ci
```

## Project Structure

```text
forge/
├── docs/               # Architecture documentation
├── tasks/              # Task tracking
├── tests/              # Unit and integration tests
├── src/
│   └── forge/          # Application package
├── Makefile            # Development commands
└── pyproject.toml      # Project configuration
```

The source tree will expand as additional components are implemented.

## Development Principles

Forge is being developed incrementally, with an emphasis on:

* Explicit module responsibilities and clear control flow.
* Minimal abstractions until concrete implementation requirements justify them.
* Automated testing and consistent code quality checks.
* Controlled dependency growth as new capabilities are introduced.
* Reproducible development and execution workflows.
