.PHONY: help install install-backend install-frontend backend frontend test lint typecheck clean

BACKEND_DIR := .
FRONTEND_DIR := frontend
VENV := .venv
PYTHON := $(VENV)/bin/python
UVICORN := $(VENV)/bin/uvicorn
NPM := npm

help:
	@echo "Sticky-Net Makefile"
	@echo "==================="
	@echo ""
	@echo "Targets:"
	@echo "  make install          Install all dependencies (backend + frontend)"
	@echo "  make install-backend  Install backend Python dependencies"
	@echo "  make install-frontend Install frontend Node.js dependencies"
	@echo "  make backend          Run the backend API server (uvicorn)"
	@echo "  make frontend         Run the frontend React dev server"
	@echo "  make test             Run backend test suite"
	@echo "  make lint             Run ruff linter on backend"
	@echo "  make typecheck        Run mypy type checker on backend"
	@echo "  make clean            Remove virtual env and node_modules"
	@echo "  make help             Show this help message"

$(VENV)/bin/activate: pyproject.toml requirements.txt
	python3.11 -m venv $(VENV)
	$(PYTHON) -m pip install -e ".[dev]"

install-backend: $(VENV)/bin/activate

install-frontend:
	$(NPM) --prefix $(FRONTEND_DIR) install --legacy-peer-deps

install: install-backend install-frontend

backend: install-backend
	$(UVICORN) src.main:app --reload --port 8000

frontend: install-frontend
	$(NPM) --prefix $(FRONTEND_DIR) start

test: install-backend
	$(PYTHON) -m pytest tests/ -v

lint: install-backend
	$(VENV)/bin/ruff check src/

typecheck: install-backend
	$(VENV)/bin/mypy src/

clean:
	rm -rf $(VENV)
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(FRONTEND_DIR)/build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
