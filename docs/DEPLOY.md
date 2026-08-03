# Деплой Enigma_PN

## Что поднимается

На одном VPS (backend): API, Bot, Worker, Postgres, Redis, Nginx, Web.
На отдельных VPS: Marzban + Xray ноды (VLESS Reality).

Домены:

- `bigwinzone.ru` — сайт
- `api.bigwinzone.ru` — API + webhooks YooMoney
- `sub.bigwinzone.ru` — subscription proxy для Happ (`/s/{token}`)

## 1. DNS

A-записи `@`, `api`, `sub` → IP backend VPS.

## 2. Backend VPS

```bash
git clone https://github.com/AlexKrit4/Enigma_PN.git
cd Enigma_PN
cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_IDS (число!),
# YOOMONEY_WALLET, YOOMONEY_NOTIFICATION_SECRET, SECRET_KEY, BOT_API_TOKEN, POSTGRES_PASSWORD
nano .env

docker compose -f docker-compose.prod.yml up -d --build
```

SSL (пример certbot на хосте):

```bash
certbot certonly --nginx -d bigwinzone.ru -d api.bigwinzone.ru -d sub.bigwinzone.ru
```

Прокиньте сертификаты в `infra/nginx/certs` или настройте host nginx как reverse proxy.

## 3. YooMoney HTTP-уведомления

В кабинете ЮMoney:

1. Кошелёк → Настройки → HTTP-уведомления
2. URL: `https://api.bigwinzone.ru/webhooks/yoomoney`
3. Секрет → `YOOMONEY_NOTIFICATION_SECRET`
4. Номер кошелька → `YOOMONEY_WALLET`

## 4. Marzban

См. [MARZBAN_SETUP.md](./MARZBAN_SETUP.md). После установки:

```env
MARZBAN_MOCK=false
MARZBAN_URL=https://panel.your-host
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=...
```

## 5. Проверка

1. `/start` у `@enigmapnbot` → пробный период
2. «Добавить в Happ» → импорт
3. Оплата тестового тарифа → webhook → active
4. Worker каждые 15 мин гасит expired

## Admin

Узнайте numeric Telegram ID через `@userinfobot`, пропишите:

```env
ADMIN_TELEGRAM_IDS=123456789
```

Команды: `/admin stats`, `/admin user ID`, `/admin extend ID DAYS`.
