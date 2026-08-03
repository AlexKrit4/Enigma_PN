#!/bin/bash
# Install on VPS: /opt/socks5/run.sh
set -euo pipefail

DIR=/opt/socks5
mkdir -p "$DIR"
touch "$DIR/passwd"
if [ ! -f "$DIR/3proxy.cfg" ]; then
  cp "$(dirname "$0")/3proxy.cfg" "$DIR/3proxy.cfg" 2>/dev/null || true
fi
if [ ! -f "$DIR/3proxy.cfg" ]; then
  cat > "$DIR/3proxy.cfg" <<'CFG'
maxconn 2000
nserver 1.1.1.1
nserver 8.8.8.8
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
log /dev/stdout
logformat "- %t %N.%p %E %U %C:%c %R:%r %O %I %h %T"
auth strong
users $/cfg/passwd
allow *
socks -p40080
monitor /cfg/passwd.reload
CFG
fi

# 3proxy "daemon" directive forks — run without it in container
sed -i '/^daemon$/d' "$DIR/3proxy.cfg" || true

docker rm -f socks5 2>/dev/null || true
docker run -d \
  --name socks5 \
  --restart unless-stopped \
  --network host \
  -v "$DIR:/cfg" \
  alpine:3.20 \
  sh -c 'apk add --no-cache 3proxy >/dev/null && exec 3proxy /cfg/3proxy.cfg'

# Host watcher: SIGHUP when API rewrites passwd / stamp
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

if ! pgrep -f '/opt/socks5/watch.sh' >/dev/null 2>&1; then
  nohup "$DIR/watch.sh" >/var/log/socks5-watch.log 2>&1 &
fi

ufw allow 40080/tcp >/dev/null 2>&1 || true
echo "SOCKS5 listening on :40080 (auth strong, users in $DIR/passwd)"
