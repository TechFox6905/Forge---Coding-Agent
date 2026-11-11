# Standalone single-package project — every recipe wraps `uv`.
.DEFAULT_GOAL := help

install:  ## Install/refresh the venv from pyproject + uv.lock, and wire git hooks.
	uv sync
	uv run pre-commit install --hook-type pre-commit --hook-type pre-push

test:  ## Run the full test suite (unit + integration).
	uv run pytest

unit-tests:  ## Run unit tests only.
	uv run pytest tests/unit

integration-tests:  ## Run integration tests only.
	uv run pytest tests/integration

lint-check:  ## Lint without writing.
	uv run ruff check

lint-fix:  ## Lint and auto-fix.
	uv run ruff check --fix

format-check:  ## Check formatting without writing.
	uv run ruff format --check

format-fix:  ## Format the code.
	uv run ruff format

pre-commit:  ## Fast gate: format-fix + lint-fix + unit tests + integration tests.
	$(MAKE) format-fix
	$(MAKE) lint-fix
	$(MAKE) test

build:  ## Build wheel + sdist into dist/.
	uv build

install-cli:  ## Put `forge` on your PATH (editable: tracks your source). Then just type `forge`.
	uv tool install --editable .
	@echo "Installed. If 'forge' is not found, add uv's tool bin to PATH: run 'uv tool update-shell' then restart your shell."

uninstall-cli:  ## Remove the `forge` command from your PATH.
	uv tool uninstall forge

ci:  ## What CI runs: lockfile check + format-check + lint-check + full tests.
	uv lock --check
	$(MAKE) format-check
	$(MAKE) lint-check
	$(MAKE) test

eval-benchmark:  ## Run the outcome benchmark across all tasks (requires keys).
	uv run python -m evals.harness.keys
	uv run python -m evals benchmark

eval-regression:  ## Run the behavior regression threshold gate (requires keys).
	uv run python -m evals.harness.keys
	uv run pytest evals/regression/test_thresholds.py

help:  ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install test unit-tests integration-tests lint-check lint-fix format-check format-fix pre-commit build install-cli uninstall-cli ci eval-benchmark eval-regression help
