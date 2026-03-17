PYTHON := venv/bin/python
PIP := venv/bin/pip

.PHONY: venv install run test init-db migrate mcp-bridge

venv:
	python3 -m venv venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run:
	$(PYTHON) -m uvicorn app.main:app --reload

test:
	$(PYTHON) -m pytest -q

init-db:
	$(PYTHON) scripts/init_db.py

migrate:
	$(PYTHON) -m alembic upgrade head

mcp-bridge:
	$(PYTHON) -m app.mcp.stdio_bridge
