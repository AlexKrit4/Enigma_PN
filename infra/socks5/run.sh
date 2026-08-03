#!/bin/bash
# SOCKS5 via sing-box on 127.0.0.1:40080; public :443 is HAProxy protocol-mux.
set -euo pipefail

DIR=/opt/socks5
LISTEN_HOST="${SOCKS5_LISTEN_HOST:-127.0.0.1}"
LISTEN_PORT="${SOCKS5_LISTEN_PORT:-40080}"
mkdir -p "$DIR"

if [ ! -f "$DIR/config.json" ]; then
  cat > "$DIR/config.json" <<EOF
{
  "log": {"level": "info", "timestamp": true},
  "inbounds": [{
    "type": "socks",
    "tag": "socks-in",
    "listen": "${LISTEN_HOST}",
    "listen_port": ${LISTEN_PORT},
    "users": [{"username": "_noop", "password": "$(openssl rand -hex 16)"}]
  }],
  "outbounds": [{"type": "direct", "tag": "direct"}]
}
EOF
fi

docker rm -f socks5 2>/dev/null || true
docker pull ghcr.io/sagernet/sing-box:latest >/dev/null
docker run -d \
  --name socks5 \
  --restart unless-stopped \
  --network host \
  -v "$DIR/config.json:/etc/sing-box/config.json:ro" \
  ghcr.io/sagernet/sing-box:latest \
  run -c /etc/sing-box/config.json

cat > "$DIR/watch.sh" <<'EOF'
#!/bin/sh
CFG=/opt/socks5/config.json
STAMP=/opt/socks5/passwd.reload
LAST=""
while true; do
  CUR="$(md5sum "$CFG" "$STAMP" 2>/dev/null | md5sum | awk '{print $1}')"
  if [ -n "$CUR" ] && [ "$CUR" != "$LAST" ]; then
    if [ -n "$LAST" ]; then
      docker restart socks5 >/dev/null 2>&1 || true
    fi
    LAST="$CUR"
  fi
  sleep 2
done
EOF
chmod +x "$DIR/watch.sh"
pkill -f '/opt/socks5/watch.sh' 2>/dev/null || true
nohup "$DIR/watch.sh" >/var/log/socks5-watch.log 2>&1 &

echo "SOCKS5 sing-box on ${LISTEN_HOST}:${LISTEN_PORT} (public via HAProxy :443)"
ss -lntp | grep ":${LISTEN_PORT}" || docker logs socks5 --tail 30
