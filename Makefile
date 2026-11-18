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

up:
	docker compose up -d

down:
	docker compose down

.PHONY: install lint type test cov demo eval seed up down


