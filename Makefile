.PHONY: install dev-api dev-worker dev-web start test lint typecheck build openapi init-db browser-smoke

install:
	uv sync --extra dev
	cd apps/web && pnpm install

init-db:
	uv run paper-setting-init

dev-api:
	uv run paper-setting-api

dev-worker:
	uv run paper-setting-worker

dev-web:
	cd apps/web && pnpm dev

start: init-db build
	uv run python scripts/start_local.py

start-v1.1:
	.venv/bin/python v1.1/run.py

browser-smoke: init-db build
	uv run python scripts/run_browser_smoke.py

test:
	uv run pytest

lint:
	uv run ruff check .
	cd apps/web && pnpm lint

typecheck:
	uv run mypy packages apps/api/src apps/worker/src apps/mcp/src
	cd apps/web && pnpm typecheck

build:
	cd apps/web && pnpm build

openapi:
	uv run python scripts/export_openapi.py
	cd apps/web && pnpm generate:api
