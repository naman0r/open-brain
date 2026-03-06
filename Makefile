PYTHON := venv/bin/python
PIP := venv/bin/pip

.PHONY: venv install run test

venv:
	python3 -m venv venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run:
	$(PYTHON) -m uvicorn app.main:app --reload

test:
	$(PYTHON) -m pytest -q

