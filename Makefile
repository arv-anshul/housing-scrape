.ONESHELL:

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON := python3

help:  ## Help command of Makefile
	@$(PYTHON) <(curl -sSL https://gist.githubusercontent.com/arv-anshul/84a87b6ac9b15f51b9b8d0cdeda33f5f/raw/f48d6fa8d2e5e5769af347e8baa2677cc254c5c6/make_help_decorator.py)

# ---------------------------------- Project Apps ---------------------------------------

.PHONY: api

api:  ## Run FastAPI instance using `uvicorn` command
	uvicorn app:app
