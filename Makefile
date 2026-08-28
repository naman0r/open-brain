PYTHON := venv/bin/python
PIP := venv/bin/pip

.PHONY: venv install test mcp mcp-http run

venv:
	python3 -m venv venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

mcp:
	$(PYTHON) -m app.mcp.server --transport stdio

mcp-http:
	$(PYTHON) -m app.mcp.server --transport streamable-http

run:
	$(PYTHON) -m uvicorn app.main:app --reload
