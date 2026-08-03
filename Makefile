.PHONY: up down logs migrate seed test bot-shell api-shell

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.seed

test:
	docker compose exec api pytest -q

api-shell:
	docker compose exec api bash

bot-shell:
	docker compose exec bot bash

restart:
	docker compose restart api bot worker

ps:
	docker compose ps
