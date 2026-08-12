#!/bin/bash
# Install on VPS as /opt/teleproxy/run.sh (keep SECRET in sync with .env MTPROTO_SECRET key part).
set -euo pipefail

SECRET_KEY="${TELEPROXY_SECRET_KEY:-}"
if [ -z "$SECRET_KEY" ] && [ -f /opt/teleproxy/data/config.toml ]; then
  SECRET_KEY=$(sed -n 's/^key = "\([^"]*\)"/\1/p' /opt/teleproxy/data/config.toml | head -1)
fi
if [ -z "$SECRET_KEY" ]; then
  echo "Set TELEPROXY_SECRET_KEY or keep an existing /opt/teleproxy/data/config.toml" >&2
  exit 1
fi

DOMAIN="${EE_DOMAIN:-bigwinzone.ru}"
BACKEND="${EE_BACKEND:-127.0.0.1:8444}"
EXTERNAL_IP="${EXTERNAL_IP:-31.76.245.81}"

docker rm -f teleproxy 2>/dev/null || true
docker run -d \
  --name teleproxy \
  --restart unless-stopped \
  --network host \
  -e DIRECT_MODE=true \
  -e SECRET="$SECRET_KEY" \
  -e EE_DOMAIN="$DOMAIN" \
  -e EE_BACKEND="$BACKEND" \
  -e PORT=443 \
  -e EXTERNAL_PORT=443 \
  -e EXTERNAL_IP="$EXTERNAL_IP" \
  -e WORKERS=1 \
  -e MAX_CONNECTIONS=2000 \
  -e STATS_PORT=8888 \
  -e STATS_ALLOW_NET=127.0.0.1/32 \
  -v /opt/teleproxy/data:/opt/teleproxy/data \
  ghcr.io/teleproxy/teleproxy:latest
