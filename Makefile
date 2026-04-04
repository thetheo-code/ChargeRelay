.PHONY: up down logs build restart test

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

restart:
	docker compose restart ocpp-server

test:
	python3 test_client.py
