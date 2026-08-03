# Установка Marzban для Enigma_PN

Пока `MARZBAN_MOCK=true` — бот и подписки работают с mock VLESS-ссылками (для разработки). Для реальных подключений установите панель.

## Рекомендуемая схема

1. **Panel VPS** — Marzban master (можно отдельный маленький VPS)
2. **Node VPS** (NL/DE/…) — Marzban Node + Xray VLESS Reality

## Быстрый старт (один сервер)

На Ubuntu 22.04+:

```bash
sudo bash -c "$(curl -sL https://github.com/Gozargah/Marzban-scripts/raw/master/marzban.sh)" @ install
```

Или по официальной документации: https://github.com/Gozargah/Marzban

1. Откройте панель, задайте admin password
2. Создайте inbound **VLESS + Reality + Vision**
3. Запомните URL панели, логин, пароль

## Подключение к Enigma_PN

В `.env` проекта:

```env
MARZBAN_MOCK=false
MARZBAN_URL=https://panel.example.com:8000
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=your_password
```

Перезапуск:

```bash
docker compose restart api worker
```

## Важно

- Не отдавайте пользователям прямой subscription URL Marzban — только `https://sub.bigwinzone.ru/s/{token}`
- Закройте панель firewall’ом (только ваш IP / VPN)
- Имя inbound в коде по умолчанию: `VLESS TCP REALITY` — переименуйте inbound в панели так же или поправьте `apps/api/app/services/marzban.py`

## Multi-node

Добавьте ноды в Marzban UI, затем обновите `VPN_NODES` в `.env`:

```json
[{"id":"nl-1","name":"🇳🇱 Netherlands","weight":100},{"id":"de-1","name":"🇩🇪 Germany","weight":90}]
```
