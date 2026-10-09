# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0

.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

init: ## generate .env with random secrets (never overwrites an existing .env)
	@if [ -f .env ]; then echo ".env exists, keeping it"; else scripts/generate-dev-secrets.sh > .env && chmod 600 .env && echo "wrote .env"; fi

up: init ## build and start the stack, wait until healthy
	docker compose up -d --build --wait

down: ## stop the stack (keep data)
	docker compose down

reset: ## stop the stack and DELETE all data volumes
	docker compose down -v

lint: ## ruff + reuse
	ruff check .
	ruff format --check .
	reuse lint

test: ## unit tests (no stack needed)
	cd services/api && uv run pytest -m "not integration"

test-integration: ## integration tests (needs `make up`)
	cd services/api && set -a && source ../../.env && set +a && uv run pytest -m integration

.PHONY: help init up down reset lint test test-integration
