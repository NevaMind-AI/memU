.PHONY: install
install:
	@echo "[install] Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

.PHONY: check
check:
	@echo "[check] Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "[check] Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "[check] Static type checking: Running mypy"
	@uv run mypy
	@echo "[check] Checking for obsolete dependencies: Running deptry"
	@uv run deptry src


.PHONY: test
test:
	@echo "[test] Running pytest"
	@uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: docs
docs:
	@echo "[docs] Serving documentation with MkDocs"
	@uv run mkdocs serve

.PHONY: docs-build
docs-build:
	@echo "[docs] Building documentation with MkDocs"
	@uv run mkdocs build --strict
