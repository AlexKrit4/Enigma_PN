# Telegram MTProto Proxy (mtg) — Enigma_PN

Прокси **только для Telegram**. Не заменяет VPN в Happ.

Официально: https://core.telegram.org/proxy  
Рекомендуемый софт: [9seconds/mtg](https://github.com/9seconds/mtg) (Fake-TLS).

## DNS (сделайте сейчас)

| Запись | Тип | Значение |
|--------|-----|----------|
| `tg.bigwinzone.ru` | **A** | IP VPS, где будет крутиться mtg |

Порт по умолчанию: **443** (Fake-TLS выглядит как HTTPS).

Если на этом же IP уже занят 443 (например Marzban Reality) — либо:
- отдельный VPS / отдельный IP под прокси, **или**
- другой порт (например `8443`) и `MTPROTO_PORT=8443` в `.env`.

## Установка mtg на VPS

```bash
# Docker
mkdir -p /opt/mtg && cd /opt/mtg

# Сгенерировать Fake-TLS secret (домен маскировки — www.google.com)
docker run --rm nineseconds/mtg:2 generate-secret --hex www.google.com
# → скопируйте вывод (начинается с ee...) в MTPROTO_SECRET

cat > /opt/mtg/config.toml <<'EOF'
secret = "ВСТАВЬТЕ_SECRET_СЮДА"
bind-to = "0.0.0.0:3128"
EOF

docker run -d \
  --name enigma-mtg \
  --restart unless-stopped \
  -v /opt/mtg/config.toml:/config.toml:ro \
  -p 443:3128 \
  nineseconds/mtg:2
```

Проверка ссылок:

```bash
docker exec enigma-mtg /mtg access /config.toml
```

Firewall: откройте TCP `443` (или ваш `MTPROTO_PORT`).

## Подключение к Enigma_PN

В `.env` backend/bot:

```env
MTPROTO_ENABLED=true
MTPROTO_HOST=tg.bigwinzone.ru
MTPROTO_PORT=443
MTPROTO_SECRET=ee........   # из generate-secret
MTPROTO_FAKE_TLS_DOMAIN=www.google.com
```

Перезапуск:

```bash
docker compose restart api bot
```

В боте у подписчика: **«🔌 Прокси Telegram»** → кнопка «Подключить прокси».

## Как это выдаётся

- API: `POST /api/v1/telegram-proxy` (только с `X-Bot-Token`)
- Без активной подписки / trial → отказ
- Пока secret/host пустые → бот пишет «настраивается»

## Связь с VPN (Happ)

| Сценарий | Что включить |
|----------|--------------|
| Только Telegram не открывается | MTProto proxy |
| Нужен весь интернет | VPN в Happ |
| Оба сразу | Можно; оптимально в Happ исключить Telegram из туннеля (routing), чтобы не было double-hop |

## Безопасность

- Secret общий на MVP — не публикуйте его вне бота.
- Оператор прокси видит IP клиентов, но не сообщения Telegram.
- Не логируйте `MTPROTO_SECRET` и полные `tg://` ссылки в открытых логах.

## Опционально: compose на том же хосте

См. `infra/mtg/` и профиль `mtg` в `docker-compose.yml` — только если порт 443 свободен на backend VPS.
