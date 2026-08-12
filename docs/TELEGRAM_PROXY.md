# Telegram MTProto Proxy — Enigma_PN

Прокси **только для Telegram**. Не заменяет VPN в Happ.

На проде используется **[teleproxy](https://github.com/teleproxy/teleproxy)** на публичном **:443** (Fake-TLS + MSS clamp).  
HAProxy **не** ставить перед teleproxy — ломает ClientHello / DPI-обход.

## DNS

| Запись | Тип | Значение |
|--------|-----|----------|
| `tg` | **A** | `31.76.245.81` |

Полное имя: **`tg.bigwinzone.ru`** (A → тот же IP). В ссылке host может быть `tg.bigwinzone.ru`, Fake-TLS domain в secret — `bigwinzone.ru`.

## Live layout

| Service | Bind | Notes |
| --- | --- | --- |
| `teleproxy` | `0.0.0.0:443` | host network; Fake-TLS + backend сайта |
| site nginx | `127.0.0.1:8444` | Let's Encrypt |
| Xray Reality | `:52250` | VPN |

Teleproxy: `EE_DOMAIN=bigwinzone.ru`, `EE_BACKEND=127.0.0.1:8444` — валидный MTProto → прокси, остальное → сайт.

## Запуск на VPS

```bash
# HAProxy must be stopped
systemctl disable --now haproxy

/opt/teleproxy/run.sh
# secret key в /opt/teleproxy/data/config.toml → MTPROTO_SECRET=ee{key}{hex(bigwinzone.ru)}
```

## .env

```env
MTPROTO_ENABLED=true
MTPROTO_HOST=tg.bigwinzone.ru
MTPROTO_PORT=443
MTPROTO_SECRET=ee........62696777696e7a6f6e652e7275
MTPROTO_FAKE_TLS_DOMAIN=bigwinzone.ru
```

```bash
cd /opt/enigma_pn && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api bot
```

В боте: удалить старый прокси → **«🔌 Прокси Telegram»** → подключить заново.

## Если снова «пинг → недоступен»

Это типичный паттерн **TSPU/DPI** в РФ: рукопожатие проходит, Application Data режется. Полностью сервером не лечится (JA4 клиента Telegram). Обход: VPN в Happ для Telegram, или клиент с обновлённым Fake-TLS.

## API

- `POST /api/v1/telegram-proxy` (только с `X-Bot-Token`)
- Нужна активная подписка / trial
