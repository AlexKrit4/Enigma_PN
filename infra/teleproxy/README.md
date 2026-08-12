# Teleproxy (MTProto) on Finland VPS

Fake-TLS MTProto must listen on **public :443**. Non-443 ports are filtered by RU DPI after the first probe.

## Live layout

| Service | Bind | Notes |
| --- | --- | --- |
| `teleproxy` | `0.0.0.0:443` | host network; Fake-TLS + MSS clamp |
| site nginx (compose) | `127.0.0.1:8444` | real Let's Encrypt TLS for `*.bigwinzone.ru` |
| Xray Reality | `:52250` | VPN — untouched |
| HTTP ACME / redirect | `:80` | still docker nginx |

Teleproxy uses the own-domain backend mode:

- `EE_DOMAIN=bigwinzone.ru`
- `EE_BACKEND=127.0.0.1:8444`

Valid Telegram proxy clients are handled by teleproxy. Everything else (browsers, probes, wrong secret, other SNIs like `api.` / `sub.`) is forwarded to nginx — so the site keeps working on https://bigwinzone.ru.

Do **not** put HAProxy/nginx stream in front of teleproxy on :443 (breaks MSS clamp / ClientHello).

## App env

```env
MTPROTO_ENABLED=true
MTPROTO_HOST=bigwinzone.ru
MTPROTO_PORT=443
MTPROTO_SECRET=ee<16-byte-key-hex><hex(bigwinzone.ru)>
```

`MTPROTO_SECRET` must match teleproxy `[[secret]].key` + domain hex from `/opt/teleproxy/data/config.toml`.

## Restart

```bash
/opt/teleproxy/run.sh
# then refresh api/bot so they pick up .env
cd /opt/enigma_pn && docker compose up -d api bot
```

HAProxy on :443 must stay **stopped/disabled** while teleproxy owns the port.
