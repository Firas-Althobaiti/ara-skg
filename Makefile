install:
	pip install -e .[dev]

lint:
	ruff check .
	black --check .

type:
	mypy ara --strict

test:
	pytest -vv

cov:
	pytest --cov=ara --cov-report=term-missing

demo:
	python scripts/demo.py

eval:
	python -m ara.eval

seed:
	python scripts/seed_neo4j.py

docs:
	mkdocs serve

docs-build:
	mkdocs build --strict

up:
	docker compose up -d

down:
	docker compose down

.PHONY: install lint type test cov demo eval seed docs docs-build up down


