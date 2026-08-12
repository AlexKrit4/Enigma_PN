# Telegram MTProto Proxy (mtg) — Enigma_PN

Прокси **только для Telegram**. Не заменяет VPN в Happ.

Официально: https://core.telegram.org/proxy  
Рекомендуемый софт: [9seconds/mtg](https://github.com/9seconds/mtg) (Fake-TLS).

## DNS

| Запись | Тип | Значение |
|--------|-----|----------|
| `tg` | **A** | `31.76.245.81` |

Полное имя: **`tg.bigwinzone.ru`**

Публичный порт: **443** (через HAProxy SNI). Сайт и прокси делят один IP.

## Как устроено на VPS

1. `enigma-mtg` слушает только `127.0.0.1:3128`
2. HAProxy на `:443`:
   - SNI `www.google.com` → mtg (Fake-TLS из secret)
   - остальное → nginx сайта (`127.0.0.1:8444`)
3. Конфиг: `infra/haproxy/haproxy-443-mtg.cfg`

**Важно:** образ `nineseconds/mtg:2` читает путь `/config/config.toml` — volume нужно монтировать именно туда (не `/config.toml`).

## Установка

```bash
bash infra/scripts/install-mtg.sh www.google.com
cp infra/haproxy/haproxy-443-mtg.cfg /etc/haproxy/haproxy.cfg
haproxy -c -f /etc/haproxy/haproxy.cfg && systemctl reload haproxy
```

## .env

```env
MTPROTO_ENABLED=true
MTPROTO_HOST=tg.bigwinzone.ru
MTPROTO_PORT=443
MTPROTO_SECRET=ee........
MTPROTO_FAKE_TLS_DOMAIN=www.google.com
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api bot
```

В боте: **«🔌 Прокси Telegram»** / `/tgproxy` → «Подключить прокси».

## API

- `POST /api/v1/telegram-proxy` (только с `X-Bot-Token`)
- Без активной подписки / trial → отказ

## Безопасность

- Secret общий на MVP — не публикуйте его вне бота.
- Оператор прокси видит IP клиентов, но не сообщения Telegram.
