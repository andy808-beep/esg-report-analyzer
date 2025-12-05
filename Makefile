.PHONY: install dev lint test clean build

# Install production dependencies
install:
	pip install -e .

# Install with dev dependencies
dev:
	pip install -e ".[dev]"

# Run linter
lint:
	ruff check src tests
	ruff format --check src tests
	mypy src

# Format code
format:
	ruff format src tests
	ruff check --fix src tests

# Run tests
test:
	pytest -v

# Run tests with coverage
coverage:
	pytest --cov=esg_analyzer --cov-report=html

# Clean build artifacts
clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

# Build package
build: clean
	python -m build

# Run the CLI
run:
	esg-analyzer --help

