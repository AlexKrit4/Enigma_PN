# SOCKS5 (3proxy) for Telegram

Per-account `username` / `password` stored in `proxy_access`, synced to `/opt/socks5/passwd`.

## Layout

| Item | Value |
| --- | --- |
| Listen | `0.0.0.0:40080` |
| Auth | strong (required) |
| Passwd | `/opt/socks5/passwd` (`user:CL:pass`) |
| Container | `socks5` (`3proxy/3proxy`, host network) |

Telegram deep link: `https://t.me/socks?server=…&port=40080&user=…&pass=…`

## App env

```env
SOCKS5_ENABLED=true
SOCKS5_HOST=bigwinzone.ru
SOCKS5_PORT=40080
SOCKS5_PASSWD_PATH=/opt/socks5/passwd
SOCKS5_CONTAINER=socks5
```

Mount `/opt/socks5` into `api` and `worker`. On grant/revoke/expire the API rewrites `passwd` and touches `passwd.reload`; host `watch.sh` sends `SIGHUP` to the container.

## Start

```bash
bash /opt/enigma_pn/infra/socks5/run.sh
# or copy run.sh to /opt/socks5/run.sh
```
