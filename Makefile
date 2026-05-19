.PHONY: install run test cov build up down smoke newman k8s clean

install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

test:
	pytest -v

cov:
	pytest --cov=app --cov-report=term-missing --cov-fail-under=70

build:
	docker build -t portfolio:dev .

up:
	docker compose up -d

down:
	docker compose down -v

smoke:
	./scripts/smoke-test.sh

newman:
	newman run postman/stock-portfolio.postman_collection.json -e postman/stock-portfolio.postman_environment.json

k8s:
	./scripts/deploy-minikube.sh

clean:
	rm -rf .pytest_cache htmlcov .coverage *.tar.gz
