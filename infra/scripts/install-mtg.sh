#!/usr/bin/env bash
# Установка mtg на отдельном VPS (запускать от root)
set -euo pipefail

DOMAIN_FRONT="${1:-www.google.com}"
HOST_PORT="${2:-443}"

mkdir -p /opt/mtg
SECRET="$(docker run --rm nineseconds/mtg:2 generate-secret --hex "$DOMAIN_FRONT")"
echo "Generated secret: $SECRET"
cat > /opt/mtg/config.toml <<EOF
secret = "$SECRET"
bind-to = "0.0.0.0:3128"
EOF

docker rm -f enigma-mtg 2>/dev/null || true
docker run -d \
  --name enigma-mtg \
  --restart unless-stopped \
  -v /opt/mtg/config.toml:/config.toml:ro \
  -p "${HOST_PORT}:3128" \
  nineseconds/mtg:2

echo "Done. Put into Enigma .env:"
echo "MTPROTO_ENABLED=true"
echo "MTPROTO_HOST=tg.bigwinzone.ru"
echo "MTPROTO_PORT=${HOST_PORT}"
echo "MTPROTO_SECRET=${SECRET}"
docker exec enigma-mtg /mtg access /config.toml || true
