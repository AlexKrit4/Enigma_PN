#!/bin/bash
# Install on VPS: /opt/socks5/run.sh
set -euo pipefail

DIR=/opt/socks5
mkdir -p "$DIR"

cat > "$DIR/3proxy.cfg" <<'CFG'
maxconn 500
nserver 1.1.1.1
nserver 8.8.8.8
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
log
auth strong
users $/etc/3proxy/passwd
allow *
socks -p40080
CFG

if [ ! -s "$DIR/passwd" ]; then
  echo '_noop:CL:disabled' > "$DIR/passwd"
fi
touch "$DIR/passwd.reload"

docker rm -f socks5 2>/dev/null || true
docker pull 3proxy/3proxy:latest >/dev/null
docker run -d \
  --name socks5 \
  --restart unless-stopped \
  --network host \
  --ulimit nofile=65535:65535 \
  -v "$DIR:/etc/3proxy" \
  3proxy/3proxy:latest

cat > "$DIR/watch.sh" <<'EOF'
#!/bin/sh
PASSWD=/opt/socks5/passwd
STAMP=/opt/socks5/passwd.reload
LAST=""
while true; do
  CUR="$(md5sum "$PASSWD" "$STAMP" 2>/dev/null | md5sum | awk '{print $1}')"
  if [ -n "$CUR" ] && [ "$CUR" != "$LAST" ]; then
    docker kill -s HUP socks5 >/dev/null 2>&1 || true
    LAST="$CUR"
  fi
  sleep 2
done
EOF
chmod +x "$DIR/watch.sh"

pkill -f '/opt/socks5/watch.sh' 2>/dev/null || true
nohup "$DIR/watch.sh" >/var/log/socks5-watch.log 2>&1 &

ufw allow 40080/tcp >/dev/null 2>&1 || true
sleep 1
ss -lntp | grep 40080 || docker logs socks5 --tail 30
echo "SOCKS5 listening on :40080 (auth strong, users in $DIR/passwd)"
