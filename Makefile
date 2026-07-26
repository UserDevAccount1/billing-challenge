PYTHON ?= python3
VENV ?= .venv

.PHONY: setup test-visible

setup:
	$(PYTHON) -m venv $(VENV)

test-visible:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v
