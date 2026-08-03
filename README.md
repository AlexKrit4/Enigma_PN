# Enigma_PN

VPN-сервис с подписками для **Happ**: Telegram-бот `@enigmapnbot`, сайт на **bigwinzone.ru**, оплата через **ЮMoney (HTTP-уведомления)**, панель **Marzban**.

## Быстрый старт (локально)

```bash
cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN, SECRET_KEY, BOT_API_TOKEN, ADMIN_TELEGRAM_IDS
docker compose up -d --build
```

- API: http://localhost:8000/health  
- Web: http://localhost:3000  
- Nginx: http://localhost:8080  

## Документация

| Файл | Содержание |
|------|------------|
| [docs/USER_SETUP_CHECKLIST.md](docs/USER_SETUP_CHECKLIST.md) | Что настроить владельцу |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Production деплой |
| [docs/MARZBAN_SETUP.md](docs/MARZBAN_SETUP.md) | Установка VPN-панели |
| [docs/HAPP_INTEGRATION.md](docs/HAPP_INTEGRATION.md) | Subscription / deep link |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Схема системы |
| [docs/AGENT_PROMPT.md](docs/AGENT_PROMPT.md) | Полный продуктовый промпт |

## Стек

FastAPI · aiogram 3 · Next.js 15 · PostgreSQL · Redis/arq · Marzban · Docker Compose

## Тарифы (seed)

**Для себя:** 100 / 299 / 999 ₽  
**Семейный:** 225 / 649 / 2249 ₽  

Пробный период: 1 день.

## Команды

```bash
make up
make logs
make migrate
make seed
make test
```
