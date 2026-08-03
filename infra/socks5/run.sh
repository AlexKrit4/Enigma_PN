#!/bin/bash
# Install on VPS: /opt/socks5/run.sh  (sing-box SOCKS5 with required user/pass)
set -euo pipefail

DIR=/opt/socks5
PORT="${SOCKS5_PORT:-40080}"
mkdir -p "$DIR"

if [ ! -f "$DIR/config.json" ]; then
  cat > "$DIR/config.json" <<EOF
{
  "log": {"level": "info", "timestamp": true},
  "inbounds": [{
    "type": "socks",
    "tag": "socks-in",
    "listen": "::",
    "listen_port": ${PORT},
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

# Restart when API rewrites config (compose has no docker.sock in api)
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

ufw allow "${PORT}/tcp" >/dev/null 2>&1 || true
sleep 1
ss -lntp | grep ":${PORT}" || docker logs socks5 --tail 40
echo "SOCKS5 (sing-box) on :${PORT}; config $DIR/config.json"
