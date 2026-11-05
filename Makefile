.PHONY: setup check test demo up down diagrams

setup: ## Install dependencies
	uv sync

check: ## Everything CI runs, except the audit
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest --cov --cov-fail-under=90
	uv run python -m triage.demo

test:
	uv run pytest

demo: ## Run the pipeline against fakes, with injected failures
	uv run python -m triage.demo

up: ## Run the API and worker in Docker
	docker compose up --build

down:
	docker compose down

diagrams: ## Rebuild docs/assets
	sh scripts/render-diagrams.sh
