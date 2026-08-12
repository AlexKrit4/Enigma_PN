# Telegram MTProto Proxy (mtg) — Enigma_PN

Прокси **только для Telegram**. Не заменяет VPN в Happ.

Официально: https://core.telegram.org/proxy  
Рекомендуемый софт: [9seconds/mtg](https://github.com/9seconds/mtg) (Fake-TLS).

## DNS

| Запись | Тип | Значение |
|--------|-----|----------|
| `tg` | **A** | `31.76.245.81` |

Полное имя: **`tg.bigwinzone.ru`**

На текущем VPS порт **443 занят HAProxy** (сайт). MTProto слушает **8443**.

## Установка mtg на VPS

```bash
bash infra/scripts/install-mtg.sh www.google.com 8443
# скрипт выведет MTPROTO_SECRET
```

Или вручную:

```bash
mkdir -p /opt/mtg
docker run --rm nineseconds/mtg:2 generate-secret --hex www.google.com
# → ee... в MTPROTO_SECRET

cat > /opt/mtg/config.toml <<'EOF'
secret = "ВСТАВЬТЕ_SECRET_СЮДА"
bind-to = "0.0.0.0:3128"
EOF

docker run -d \
  --name enigma-mtg \
  --restart unless-stopped \
  -v /opt/mtg/config.toml:/config.toml:ro \
  -p 8443:3128 \
  nineseconds/mtg:2

ufw allow 8443/tcp || true
```

## .env

```env
MTPROTO_ENABLED=true
MTPROTO_HOST=tg.bigwinzone.ru
MTPROTO_PORT=8443
MTPROTO_SECRET=ee........
MTPROTO_FAKE_TLS_DOMAIN=www.google.com
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api bot
```

В боте у подписчика: **«🔌 Прокси Telegram»** / `/tgproxy` → «Подключить прокси».

## API

- `POST /api/v1/telegram-proxy` (только с `X-Bot-Token`)
- Без активной подписки / trial → отказ
- Пока secret/host пустые → «настраивается»

## Безопасность

- Secret общий на MVP — не публикуйте его вне бота.
- Оператор прокси видит IP клиентов, но не сообщения Telegram.
