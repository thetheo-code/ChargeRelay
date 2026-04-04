.PHONY: up down logs build restart

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
