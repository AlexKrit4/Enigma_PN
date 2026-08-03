# SOCKS5 (sing-box) for Telegram

Per-account `username` / `password` in `proxy_access`, synced into `/opt/socks5/config.json`.

## Layout

| Item | Value |
| --- | --- |
| Listen | `0.0.0.0:40080` |
| Auth | required (sing-box `users`) |
| Config | `/opt/socks5/config.json` |
| Container | `socks5` (`ghcr.io/sagernet/sing-box`) |

Telegram: `https://t.me/socks?server=…&port=40080&user=…&pass=…`

## App env

```env
SOCKS5_ENABLED=true
SOCKS5_HOST=bigwinzone.ru
SOCKS5_PORT=40080
SOCKS5_PASSWD_PATH=/opt/socks5/passwd
SOCKS5_CONTAINER=socks5
```

`api`/`worker` mount `/opt/socks5`. On grant/revoke/expire they rewrite `config.json` + touch `passwd.reload`; host `watch.sh` restarts the container.

## Start

```bash
bash /opt/enigma_pn/infra/socks5/run.sh
```
