# SOCKS5 (sing-box) + HAProxy :443 mux

RU DPI often hangs plain SOCKS on high ports. Public entry is **:443**:

| Traffic | First byte | Backend |
| --- | --- | --- |
| SOCKS5 | `0x05` | `127.0.0.1:40080` sing-box |
| HTTPS site/API | TLS ClientHello | `127.0.0.1:8444` nginx |

## Env

```env
SOCKS5_ENABLED=true
SOCKS5_HOST=bigwinzone.ru
SOCKS5_PORT=443
SOCKS5_LISTEN_HOST=127.0.0.1
SOCKS5_LISTEN_PORT=40080
SOCKS5_PASSWD_PATH=/opt/socks5/passwd
SOCKS5_CONTAINER=socks5
```

## Start

```bash
bash /opt/enigma_pn/infra/socks5/run.sh
cp /opt/enigma_pn/infra/socks5/haproxy-443.cfg /etc/haproxy/haproxy.cfg
systemctl restart haproxy
# teleproxy must NOT bind :443
docker rm -f teleproxy 2>/dev/null || true
```
