# Чеклист владельца — Enigma_PN

## Сделано в конфиге проекта

- [x] Бренд: **Enigma_PN**
- [x] Бот: **@enigmapnbot** (токен положить только в `.env`, не в git)
- [x] Домен: **bigwinzone.ru** (`api.`, `sub.`)
- [x] Платежи: **ЮMoney HTTP-уведомления**
- [x] Тарифы: «для себя» / «семейный» (засеяны в seed)
- [x] Пробный период: **1 день, 5 GB, 1 устройство**
- [x] Marzban: mock + инструкция `docs/MARZBAN_SETUP.md`

## Сделать вам сейчас

### 1. Telegram numeric ID (обязательно для админки)

Вы указали `@alexkr1t` — это username. Нужен **числовой** ID:

1. Напишите боту [@userinfobot](https://t.me/userinfobot)
2. Или напишите `/start` боту `@enigmapnbot` — он покажет ID, если `ADMIN_TELEGRAM_IDS` пуст
3. Пропишите в `.env`: `ADMIN_TELEGRAM_IDS=ВАШ_ЧИСЛОВОЙ_ID`

### 2. Секреты в `.env`

```bash
cp .env.example .env
```

Заполните:

- [ ] `TELEGRAM_BOT_TOKEN` — токен от BotFather
- [ ] `ADMIN_TELEGRAM_IDS` — числовой ID
- [ ] `SECRET_KEY` — `openssl rand -hex 32`
- [ ] `BOT_API_TOKEN` — `openssl rand -hex 24`
- [ ] `POSTGRES_PASSWORD` — сильный пароль
- [ ] `YOOMONEY_WALLET` — номер кошелька
- [ ] `YOOMONEY_NOTIFICATION_SECRET` — секрет HTTP-уведомлений

### 3. ЮMoney

- [ ] В кабинете ЮMoney включить HTTP-уведомления
- [ ] URL: `https://api.bigwinzone.ru/webhooks/yoomoney`
- [ ] Прописать wallet + secret в `.env`

### 4. DNS

- [ ] A `@` → IP backend VPS
- [ ] A `api` → IP backend VPS
- [ ] A `sub` → IP backend VPS

### 5. VPS + Marzban

- [ ] Backend VPS (Docker) — см. `docs/DEPLOY.md`
- [ ] Установить Marzban — см. `docs/MARZBAN_SETUP.md`
- [ ] `MARZBAN_MOCK=false` после установки панели

### 6. Безопасность токена

Токен бота был отправлен в чат. Рекомендуется **перевыпустить** токен в BotFather (`/revoke`) и обновить `.env`.

## Финальная проверка

- [ ] `/start` → trial
- [ ] Happ import работает (после Marzban)
- [ ] Оплата ЮMoney активирует подписку
- [ ] `/admin stats` отвечает
