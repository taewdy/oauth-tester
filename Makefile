.PHONY: help install install-dev run test lint lint-ruff format type-check clean build all

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  run          - Run the FastAPI development server"
	@echo "  certs        - Generate local self-signed TLS certs in certs/"
	@echo "  certs-mkcert - Generate locally trusted certs via mkcert"
	@echo "  run-prod     - Run the server using app settings"
	@echo "  test         - Run tests"
	@echo "  lint         - Run all linting tools (ruff, format-check, type-check)"
	@echo "  lint-ruff    - Run ruff (lint + format)"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run mypy type checking"
	@echo "  clean        - Clean build artifacts and cache"
	@echo "  build        - Build the package"
	@echo "  all          - Install deps, lint, test, and build"

# Install production dependencies
install:
	uv sync --no-dev

# Install development dependencies
install-dev:
	uv sync

# Run the FastAPI development server
run:
	# Use module entrypoint so SSL from env is applied
	uv run python -m oauth_tester.main

# Run the server using main entry (uses settings)
run-prod:
	uv run python -m oauth_tester.main

# Generate local self-signed TLS certs for https://localhost:8000
certs:
	mkdir -p certs
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	  -keyout certs/localhost.key -out certs/localhost.crt \
	  -subj "/CN=localhost" \
	  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
	@echo "Generated certs/localhost.crt and certs/localhost.key"

# Generate trusted local certs using mkcert (recommended)
# Requires: https://github.com/FiloSottile/mkcert installed
certs-mkcert:
	mkdir -p certs
	mkcert -install
	mkcert -key-file certs/localhost.key -cert-file certs/localhost.crt localhost 127.0.0.1 ::1
	@echo "Generated locally trusted certs/localhost.crt and certs/localhost.key"

# Run tests
test:
	uv run pytest -v

# Run tests with coverage
test-cov:
	uv run pytest --cov=oauth_tester --cov-report=html --cov-report=term

# Format code with black and isort
format:
	uv run black src/
	uv run isort src/

# Check code formatting (without making changes)
format-check:
	uv run black --check src/
	uv run isort --check-only src/

# Run mypy type checking
type-check:
	uv run mypy src/

# Run all linting tools
lint: lint-ruff format-check type-check

# Ruff lint (auto-fix safe rules and format)
lint-ruff:
	uv run ruff check --fix .
	uv run ruff format .

# Run all linting tools and fix issues where possible
lint-fix: format type-check

# Clean build artifacts and cache
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Build the package
build: clean
	uv build

# Run the complete development workflow
all: install-dev lint test build

# Development setup - run this first
setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make run' to start the development server"

# Show project info

info:
	@echo "Project: oauth-tester"
	@echo "Python: >=3.11"
	@echo "Package Manager: uv"
	@echo "Framework: FastAPI"
	@echo ""
	@echo "Available scripts:"
	@uv run --help | grep -A 20 "Available commands:"
