.PHONY: help clean test coverage lint format build upload install-dev install

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install: ## Install package
	pip install .

install-dev: ## Install package in development mode
	pip install -e ".[dev]"

test: ## Run tests
	pytest

coverage: ## Run tests with coverage
	pytest --cov=memu --cov-report=html --cov-report=term

lint: ## Run linting
	flake8 memu tests
	mypy memu

format: ## Format code
	black memu tests
	isort memu tests

build: clean ## Build package
	python -m build

upload-test: build ## Upload to TestPyPI
	python -m twine upload --repository testpypi dist/*

upload: build ## Upload to PyPI
	python -m twine upload dist/*

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files 