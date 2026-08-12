#!/usr/bin/env bash
# Установка mtg на VPS (запускать от root).
# Образ nineseconds/mtg:2 читает /config/config.toml — монтируем именно туда.
# На Enigma VPS публичный :443 = HAProxy (SNI www.google.com → mtg, иначе сайт).
# mtg слушает только 127.0.0.1:3128.
set -euo pipefail

DOMAIN_FRONT="${1:-www.google.com}"
# Local bind only; public port is 443 via HAProxy (see infra/haproxy/haproxy-443-mtg.cfg)
BIND_PORT="${2:-3128}"

mkdir -p /opt/mtg /config 2>/dev/null || mkdir -p /opt/mtg
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
  -v /opt/mtg/config.toml:/config/config.toml:ro \
  -p "127.0.0.1:${BIND_PORT}:3128" \
  nineseconds/mtg:2 run /config/config.toml

echo "Done. Put into Enigma .env:"
echo "MTPROTO_ENABLED=true"
echo "MTPROTO_HOST=tg.bigwinzone.ru"
echo "MTPROTO_PORT=443"
echo "MTPROTO_SECRET=${SECRET}"
echo "MTPROTO_FAKE_TLS_DOMAIN=${DOMAIN_FRONT}"
echo ""
echo "HAProxy must route SNI ${DOMAIN_FRONT} → 127.0.0.1:${BIND_PORT}"
echo "See infra/haproxy/haproxy-443-mtg.cfg"
docker exec enigma-mtg /mtg access /config/config.toml || true
