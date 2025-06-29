# Makefile for File Duplicate Finder
# Provides convenient commands for building, testing, and packaging

.PHONY: help install test clean build pypi standalone docker release all

# Default target
help:
	@echo "File Duplicate Finder - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install package in development mode"
	@echo "  test        - Run tests"
	@echo "  clean       - Clean build artifacts"
	@echo ""
	@echo "Building:"
	@echo "  build       - Build PyPI package"
	@echo "  pypi        - Build and upload to PyPI"
	@echo "  standalone  - Build standalone executables"
	@echo "  docker      - Build Docker image"
	@echo "  release     - Build all packages for release"
	@echo "  all         - Build everything (PyPI + standalone + Docker)"
	@echo ""
	@echo "Platform-specific:"
	@echo "  linux       - Build for Linux"
	@echo "  windows     - Build for Windows"
	@echo "  macos       - Build for macOS"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make test"
	@echo "  make standalone"
	@echo "  make docker"

# Development commands
install:
	pip install -e ".[dev,gui]"

test:
	pytest tests/ -v

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Building commands
build:
	python build.py pypi

pypi: build
	@echo "PyPI package built successfully!"
	@echo "To upload to PyPI, run: twine upload dist/*"

standalone:
	python build.py standalone

docker:
	python build.py docker

release: clean
	python build.py all

all: clean
	python build.py all

# Platform-specific builds
linux:
	python build.py standalone linux

windows:
	python build.py standalone windows

macos:
	python build.py standalone macos

# Docker commands
docker-build:
	docker build -t filedupfinder:latest .

docker-run:
	docker run -v $(PWD):/app/data filedupfinder:latest /app/data

docker-push:
	docker tag filedupfinder:latest yourusername/filedupfinder:latest
	docker push yourusername/filedupfinder:latest

# Testing commands
test-coverage:
	pytest tests/ --cov=filedupfinder --cov-report=html

test-lint:
	black --check src/ tests/
	mypy src/

test-all: test test-lint

# Development setup
setup-dev:
	pip install -e ".[dev,gui]"
	pre-commit install

# Documentation
docs:
	@echo "Building documentation..."
	# Add documentation building commands here

# Release preparation
pre-release:
	@echo "Preparing for release..."
	@echo "1. Update version in pyproject.toml"
	@echo "2. Update version in version_info.txt"
	@echo "3. Update CHANGELOG.md"
	@echo "4. Run: make test-all"
	@echo "5. Run: make release"

# Quick commands
quick-test:
	python -m pytest tests/ -x

quick-build:
	python build.py pypi

quick-run:
	python -m filedupfinder --demo

# Platform detection
detect-platform:
	@echo "Detected platform: $(shell python -c 'import platform; print(platform.system().lower())')"

# Help for specific commands
help-build:
	@echo "Build Commands:"
	@echo "  make build       - Build PyPI package only"
	@echo "  make standalone  - Build standalone executable for current platform"
	@echo "  make docker      - Build Docker image"
	@echo "  make all         - Build everything"

help-test:
	@echo "Test Commands:"
	@echo "  make test        - Run all tests"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo "  make test-lint   - Run linting checks"
	@echo "  make test-all    - Run all tests and checks"

help-docker:
	@echo "Docker Commands:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make docker-push  - Push to Docker Hub" 