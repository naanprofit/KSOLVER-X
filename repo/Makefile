PYTHON?=python3
PIP?=$(PYTHON) -m pip

.DEFAULT_GOAL := help

.PHONY: help install lint format test run-demo run-demo-71bit build-bloom gen-traps schedule worker

help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:' Makefile | sed 's/:.*//' | grep -v '^help$$' | xargs -n1 echo ' -'

install:
	$(PIP) install -r requirements.txt

lint:
	ruff check src tests

format:
	ruff check --select I --fix src tests
	ruff format src tests

test:
	pytest

run-demo:
	bash scripts/demo_small_range.sh

run-demo-71bit:
	bash scripts/demo_71bit_target.sh

build-bloom:
	$(PYTHON) -m cli.trap_tools build-bloom

gen-traps:
	$(PYTHON) -m cli.trap_tools generate

schedule:
	$(PYTHON) -m cli.crt_tools schedule

worker:
	$(PYTHON) -m cli.run_worker
