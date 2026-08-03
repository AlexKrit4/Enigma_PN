#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose -f docker-compose.prod.yml pull || true
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head
docker compose -f docker-compose.prod.yml exec -T api python -m app.seed
echo "Deployed. Check: docker compose -f docker-compose.prod.yml ps"
