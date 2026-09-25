.PHONY: setup data test lint typecheck experiments api frontend dev all

setup:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

data:
	.venv/bin/python scripts/fetch_data.py

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/ruff check mirage experiments scripts tests

typecheck:
	.venv/bin/python -m mypy mirage --ignore-missing-imports --follow-imports=skip 2>/dev/null || true

experiments:
	.venv/bin/python -m experiments.run_all

api:
	.venv/bin/uvicorn mirage.api:app --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm ci && npm run build

dev:
	cd frontend && npm run dev
