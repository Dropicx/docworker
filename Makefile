.PHONY: help install install-dev lint format typecheck test clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

install-dev:  ## Install development dependencies
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm install

# Backend Code Quality
lint-backend:  ## Lint backend code with ruff
	cd backend && ruff check app/

format-backend:  ## Format backend code with ruff
	cd backend && ruff format app/

format-backend-check:  ## Check if backend code is formatted
	cd backend && ruff format --check app/

typecheck-backend:  ## Type check backend code with mypy
	cd backend && mypy app/

audit-backend:  ## Security audit backend dependencies
	cd backend && pip-audit

# Frontend Code Quality
lint-frontend:  ## Lint frontend code with ESLint
	cd frontend && npm run lint

format-frontend:  ## Format frontend code with Prettier
	cd frontend && npm run format

format-frontend-check:  ## Check if frontend code is formatted
	cd frontend && npm run format:check

# Combined Commands
lint: lint-backend lint-frontend  ## Lint all code

format: format-backend format-frontend  ## Format all code

format-check: format-backend-check format-frontend-check  ## Check formatting

typecheck: typecheck-backend  ## Type check all code

# Testing
test-backend:  ## Run backend tests
	cd backend && pytest

test-frontend:  ## Run frontend tests
	cd frontend && npm test

test: test-backend test-frontend  ## Run all tests

test-coverage:  ## Run tests with coverage
	cd backend && pytest --cov=app --cov-report=html --cov-report=term

# Quality Checks (run before commit)
check: lint typecheck test  ## Run all quality checks

# Clean
clean:  ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Development
run-backend:  ## Run backend development server
	cd backend && python -m uvicorn app.main:app --reload --port 9122

run-frontend:  ## Run frontend development server
	cd frontend && npm run dev

# Database
migrate:  ## Run database migrations
	cd backend && python app/database/migrations/add_feature_flags.py

seed:  ## Seed database with initial data
	cd backend && python app/database/seed_document_classes.py

# Docker
docker-build:  ## Build Docker containers
	docker-compose build

docker-up:  ## Start Docker containers
	docker-compose up -d

docker-down:  ## Stop Docker containers
	docker-compose down

docker-logs:  ## View Docker logs
	docker-compose logs -f

# Pre-commit Hook Setup
setup-git-hooks:  ## Setup git pre-commit hooks
	@echo "#!/bin/sh" > .git/hooks/pre-commit
	@echo "make format-check && make lint && make typecheck" >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Git pre-commit hook installed"
