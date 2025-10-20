.PHONY: install-pre-commit lint lint-python lint-frontend format typecheck test

install-pre-commit:
	pre-commit install

lint: lint-python lint-frontend

lint-python:
	ruff check app tests
	black --check app tests
	isort --check-only app tests

lint-frontend:
	cd frontend && npm run lint

format:
	black app tests
	isort app tests
	cd frontend && npm run format

typecheck:
	mypy app tests

test:
	pytest
