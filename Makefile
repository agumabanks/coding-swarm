.PHONY: install test test-watch lint format format-check build clean dev

install:
	python tools/bootstrap.py

test:
	. .venv/bin/activate && pytest tests/ -v --tb=short

test-watch:
	. .venv/bin/activate && ptw tests/

lint:
	. .venv/bin/activate && ruff check packages/ && mypy packages/

format:
	. .venv/bin/activate && black packages/ && ruff check --fix packages/

format-check:
	. .venv/bin/activate && black --check packages/

build:
	hatch -C packages/core build
	hatch -C packages/agents build
	hatch -C packages/orchestrator build
	hatch -C packages/plugins build
	hatch -C packages/api build
	hatch -C packages/cli build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -name "*.pyc" -delete

dev:
	. .venv/bin/activate && uvicorn coding_swarm_api.main:app --reload --port 8000
