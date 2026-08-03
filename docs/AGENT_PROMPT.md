# AGENT PROMPT — Enigma_PN

> **Как использовать:** скопируй содержимое этого файла (или приложи файл целиком) в новый чат с продвинутой нейросетью (Claude Opus, GPT-5 и т.п.) в репозитории `https://github.com/AlexKrit4/Enigma_PN`. Агент должен прочитать промпт, задать владельцу проекта уточняющие вопросы, получить секреты и реализовать систему.

---

## Роль

Ты — senior full-stack инженер и DevOps. Твоя задача — **с нуля спроектировать и реализовать** коммерческий VPN-сервис с подписками для клиента **Happ**, продажей через **Telegram-бот** и **сайт**, в репозитории **Enigma_PN**.

Репозиторий сейчас пустой (только README). Ты создаёшь весь проект: код, конфиги, документацию, Docker Compose, `.env.example`, инструкции по деплою.

**Перед написанием кода** — задай владельцу проекта (пользователю) структурированный опросник из раздела «Что запросить у владельца». Не начинай интеграции с внешними сервисами, пока не получишь нужные данные или явное «поставь заглушку / mock».

---

## Контекст продукта

### Что такое Happ

**Happ** — бесплатный кроссплатформенный VPN/прокси-клиент на базе Xray. Он **не продаёт серверы** и **не выдаёт подписки**. Пользователь импортирует subscription URL от стороннего провайдера.

- Официальный сайт: https://www.happ.su/main
- Документация для разработчиков: https://www.happ.su/main/ru/dev-docs.md
- Поддерживаемые протоколы: VLESS (Reality), VMess, Trojan, Shadowsocks, Hysteria2
- Импорт: URL, QR, deep link `happ://`
- Расширения для провайдеров: Provider ID, HWID-лимиты, шифрование подписок, routing через подписку

### Что мы продаём

Мы — **VPN-провайдер**. Продаём доступ к **своим** серверам. Happ — только клиент для подключения.

Пользовательский путь:
1. Регистрация / `/start` в Telegram-боте или на сайте
2. Пробный период или покупка тарифа
3. Оплата
4. Получение subscription URL (и кнопки «Добавить в Happ»)
5. Импорт в Happ → подключение к нашим серверам

---

## Архитектура (обязательная)

```
┌─────────────────────────────────────────────────────────────────┐
│                         КЛИЕНТЫ                                  │
│   Telegram Bot  │  Telegram Mini App (опц.)  │  Web (Next.js)   │
│   Happ App ← subscription URL ← Subscription Proxy               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND API (FastAPI)                       │
│  auth │ users │ plans │ orders │ payments │ subscriptions       │
│  provisioning │ subscription-proxy │ notifications │ admin       │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
┌──────▼──────┐   ┌───────▼───────┐   ┌───────▼──────────────────┐
│ PostgreSQL  │   │ Redis + Queue │   │ VPN Panel (Marzban)      │
│             │   │ (arq/Celery)  │   │ REST API → Xray nodes    │
└─────────────┘   └───────────────┘   └──────────────────────────┘
```

### Ключевой принцип: Subscription Proxy

**Не отдавай пользователю прямой URL панели Marzban/3x-ui.**

Выдавай URL вида:
```
https://sub.{DOMAIN}/s/{opaque_token}
```

Прокси:
1. Проверяет активность подписки, трафик, срок, HWID-лимит
2. Запрашивает конфиг у Marzban API (с кэшем в Redis, TTL 2–5 мин)
3. Обогащает ответ для Happ: `profile-title`, флаги стран, routing rules, Provider ID
4. Отдаёт тело подписки в формате, понятном Happ

Это даёт контроль доступа, смену нод без перевыдачи ссылок и брендинг.

### Provisioning (асинхронно)

```
Оплата подтверждена (webhook)
  → order.status = paid
  → job: provision_subscription(order_id)
      → выбрать ноду (least-load)
      → Marzban API: создать user (VLESS + Reality)
      → сохранить uuid, node_id, sub_token в БД
      → subscription.status = active
      → уведомить пользователя (sub URL + happ:// deep link + QR)
```

Cron-задачи:
- `expire_subscriptions` — каждые 15 мин, disable в панели
- `traffic_warnings` — 80% / 100% трафика
- `renewal_reminders` — за 3 дня до окончания
- `health_check_nodes` — алерт админу в Telegram

---

## Технологический стек (зафиксирован)

| Слой | Технология | Обоснование |
|------|------------|-------------|
| Backend API | **Python 3.12 + FastAPI** | async, типизация, OpenAPI из коробки |
| Telegram Bot | **aiogram 3.x** | стандарт для async Python ботов |
| Очередь задач | **Redis + arq** | лёгче Celery для MVP |
| БД | **PostgreSQL 16** | пользователи, заказы, подписки |
| ORM | **SQLAlchemy 2.0 + Alembic** | миграции |
| VPN-панель | **Marzban** | REST API, multi-node, subscription links |
| Протокол | **VLESS + Reality + Vision** | устойчивость в РФ/СНГ 2026 |
| Frontend (сайт) | **Next.js 15 (App Router) + Tailwind** | лендинг + ЛК |
| Admin | **Next.js** или встроенная admin-sec в API | управление тарифами, пользователями |
| Reverse proxy | **Nginx** | SSL termination, routing |
| Контейнеризация | **Docker Compose** | dev + prod |
| Мониторинг (MVP+) | **Uptime Kuma** (опционально) | health checks |

**Не используй** 3x-ui, если нет явной просьбы владельца — Marzban проще для multi-node и REST API.

---

## Структура репозитория (создай)

```
Enigma_PN/
├── README.md
├── .env.example                 # все переменные с комментариями
├── docker-compose.yml           # dev
├── docker-compose.prod.yml      # production
├── Makefile                     # up, down, migrate, seed
│
├── apps/
│   ├── api/                     # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   ├── schemas/         # Pydantic
│   │   │   ├── routers/         # auth, plans, orders, sub proxy, admin, webhooks
│   │   │   ├── services/        # payment, provisioning, marzban, happ
│   │   │   ├── workers/         # arq tasks
│   │   │   └── deps.py
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── bot/                     # Telegram bot (aiogram)
│   │   ├── bot/
│   │   │   ├── main.py
│   │   │   ├── handlers/        # start, plans, buy, mysub, help, support
│   │   │   ├── keyboards/
│   │   │   ├── middlewares/
│   │   │   └── api_client.py    # HTTP к backend API
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── web/                     # Next.js сайт
│       ├── src/app/             # landing, pricing, dashboard, pay, legal
│       ├── src/components/
│       ├── Dockerfile
│       └── package.json
│
├── infra/
│   ├── nginx/
│   │   ├── default.conf
│   │   └── ssl.conf
│   ├── marzban/                 # пример env для Marzban
│   └── scripts/
│       ├── init-db.sh
│       ├── backup-db.sh
│       └── deploy.sh
│
└── docs/
    ├── AGENT_PROMPT.md          # этот файл
    ├── ARCHITECTURE.md
    ├── DEPLOY.md
    ├── HAPP_INTEGRATION.md
    └── USER_SETUP_CHECKLIST.md  # что должен сделать владелец
```

---

## Схема базы данных (реализуй)

```sql
-- users
id              UUID PK
telegram_id     BIGINT UNIQUE NULL
email           VARCHAR UNIQUE NULL
username        VARCHAR NULL
referral_code   VARCHAR(16) UNIQUE
referred_by_id  UUID FK users NULL
is_admin        BOOLEAN DEFAULT false
created_at      TIMESTAMPTZ

-- plans
id              UUID PK
slug            VARCHAR UNIQUE          -- "monthly", "quarterly"
name            VARCHAR                 -- "1 месяц"
duration_days   INT
traffic_gb      INT NULL                -- NULL = unlimited
device_limit    INT DEFAULT 2           -- HWID limit для Happ
price_rub       DECIMAL(10,2)
price_stars     INT NULL
is_active       BOOLEAN DEFAULT true
sort_order      INT

-- orders
id              UUID PK
user_id         UUID FK
plan_id         UUID FK
amount          DECIMAL(10,2)
currency        VARCHAR                 -- RUB, XTR (Stars)
status          ENUM pending|paid|failed|refunded
payment_provider VARCHAR                -- yookassa, cryptopay, stars
payment_external_id VARCHAR NULL
created_at      TIMESTAMPTZ
paid_at         TIMESTAMPTZ NULL

-- subscriptions
id              UUID PK
user_id         UUID FK
plan_id         UUID FK
order_id        UUID FK NULL
status          ENUM trial|active|expired|disabled
starts_at       TIMESTAMPTZ
ends_at         TIMESTAMPTZ
traffic_used_gb DECIMAL(10,3) DEFAULT 0
sub_token       VARCHAR(64) UNIQUE      -- opaque token для /s/{token}
marzban_username VARCHAR
marzban_uuid    UUID
node_id         VARCHAR NULL

-- payments (audit log)
id              UUID PK
order_id        UUID FK
provider        VARCHAR
external_id     VARCHAR
status          VARCHAR
raw_payload     JSONB
created_at      TIMESTAMPTZ

-- vpn_nodes (registry)
id              VARCHAR PK              -- "nl-1", "de-1"
name            VARCHAR                 -- "🇳🇱 Netherlands"
marzban_node_url VARCHAR NULL
weight          INT DEFAULT 100
is_enabled      BOOLEAN DEFAULT true
max_users       INT NULL
current_users   INT DEFAULT 0

-- support_tickets (опционально MVP+)
```

Индексы: `users.telegram_id`, `subscriptions.sub_token`, `subscriptions.status + ends_at`, `orders.status`.

---

## API Endpoints (реализуй)

### Public
```
GET  /health
GET  /api/v1/plans                          # список тарифов
POST /api/v1/auth/telegram                  # Telegram Login Widget / initData
GET  /api/v1/me                             # профиль + активная подписка
POST /api/v1/orders                         # создать заказ
GET  /api/v1/orders/{id}                    # статус заказа
GET  /s/{sub_token}                         # Subscription Proxy для Happ
```

### Webhooks (без auth, с верификацией подписи)
```
POST /webhooks/yookassa
POST /webhooks/cryptopay
POST /webhooks/telegram-stars               # через bot pre_checkout
```

### Admin (JWT или Telegram admin ID)
```
GET    /admin/users
GET    /admin/subscriptions
POST   /admin/subscriptions/{id}/extend
POST   /admin/subscriptions/{id}/disable
CRUD   /admin/plans
GET    /admin/stats                         # MRR, active subs, traffic
```

---

## Telegram Bot — сценарии (реализуй)

| Команда / кнопка | Действие |
|------------------|----------|
| `/start` | Приветствие, регистрация, пробный период (если новый) |
| `/plans` или «Тарифы» | Inline-клавиатура с тарифами |
| «Купить {тариф}» | Создать order → ссылка на оплату или invoice |
| `/mysub` или «Моя подписка» | Статус, трафик, срок, subscription URL |
| «Добавить в Happ» | `happ://import?url={encoded_sub_url}` deep link |
| «QR-код» | QR с subscription URL |
| `/help` | Инструкция: скачать Happ → импорт → подключиться |
| `/support` | Пересылка сообщения админу или тикет |

**Пробный период:** 1 день, 5 GB, 1 устройство — настраивается через env.

**Админ-команды** (только для `ADMIN_TELEGRAM_IDS`):
- `/admin stats`
- `/admin user {telegram_id}`
- `/admin extend {telegram_id} {days}`

---

## Happ Integration (реализуй по документации)

Файл `docs/HAPP_INTEGRATION.md` + код в `services/happ.py`:

1. **Subscription response headers** — `profile-title`, `subscription-userinfo` (upload/download/total/expire)
2. **Provider ID** — зарегистрировать у Happ (опционально, запросить у владельца)
3. **Deep link:** `happ://import?url=https%3A%2F%2Fsub.domain.ru%2Fs%2F{token}`
4. **Routing rules** — через subscription body (российские IP/CIDR → direct, остальное → proxy)
5. **HWID limit** — через Happ HWID links или ограничение device_limit в Marzban
6. **Emoji/flags** — в названиях серверов: `🇳🇱 Netherlands`, `🇩🇪 Germany`

Ссылки на документацию:
- https://www.happ.su/main/ru/dev-docs/hwid-ssylki.md
- https://www.happ.su/main/ru/dev-docs/routing.md
- https://www.happ.su/main/ru/dev-docs/provider-id.md
- https://www.happ.su/main/ru/dev-docs/app-management.md

---

## Платежи (реализуй с plug-in архитектурой)

```python
class PaymentProvider(Protocol):
    async def create_payment(order: Order) -> PaymentRedirect: ...
    async def verify_webhook(request: Request) -> PaymentResult: ...
```

Провайдеры (включай только те, что выбрал владелец):

| Провайдер | Env-переменные | Примечание |
|-----------|----------------|------------|
| **ЮKassa** | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` | нужно ИП/ООО |
| **Crypto Pay** | `CRYPTOPAY_API_TOKEN` | @CryptoBot, быстрый старт |
| **Telegram Stars** | встроено в bot | `XTR`, pre_checkout_query |
| **YooMoney** | `YOOMONEY_TOKEN`, `YOOMONEY_WALLET` | P2P, проще для физлица |

Webhook handler **обязательно идемпотентный**: один `external_payment_id` → одна активация подписки.

---

## Переменные окружения (.env.example)

Создай `.env.example` со **всеми** переменными и русскими комментариями:

```env
# === ОБЯЗАТЕЛЬНО ЗАПОЛНИТЬ ВЛАДЕЛЬЦУ ===

# Telegram
TELEGRAM_BOT_TOKEN=                    # @BotFather → /newbot
TELEGRAM_BOT_USERNAME=                 # без @
ADMIN_TELEGRAM_IDS=123456789,987654321 # через запятую

# Домен
DOMAIN=example.com                     # основной домен
SUB_DOMAIN=sub.example.com             # subscription proxy
API_DOMAIN=api.example.com             # backend API
WEB_DOMAIN=example.com                 # сайт

# База данных
POSTGRES_USER=enigma
POSTGRES_PASSWORD=                       # сгенерируй надёжный
POSTGRES_DB=enigma_pn
DATABASE_URL=postgresql+asyncpg://enigma:PASSWORD@postgres:5432/enigma_pn

# Redis
REDIS_URL=redis://redis:6379/0

# JWT / Secrets
SECRET_KEY=                            # openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

# Marzban
MARZBAN_URL=https://panel.example.com  # URL панели
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=
MARZBAN_SUBSCRIPTION_PREFIX=https://sub.example.com/s  # наш proxy, не Marzban напрямую

# VPN Nodes (JSON или отдельные переменные)
VPN_NODES=[{"id":"nl-1","name":"🇳🇱 Netherlands","weight":100}]

# Платежи (заполни нужные)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
CRYPTOPAY_API_TOKEN=
YOOMONEY_TOKEN=
YOOMONEY_WALLET=

# Бизнес-настройки
TRIAL_ENABLED=true
TRIAL_DURATION_DAYS=1
TRIAL_TRAFFIC_GB=5
TRIAL_DEVICE_LIMIT=1
DEFAULT_DEVICE_LIMIT=2

# Happ
HAPP_PROVIDER_ID=                      # опционально, от Happ
HAPP_PROFILE_TITLE=Enigma VPN

# Брендинг
BRAND_NAME=Enigma VPN
SUPPORT_TELEGRAM=@your_support
```

---

## Что запросить у владельца проекта (ОБЯЗАТЕЛЬНО)

**В самом начале работы** выведи владельцу структурированный чеклист. Раздели на «нужно сейчас» и «можно позже».

### 🔴 Нужно для старта разработки

1. **Название бренда** — как называется сервис (по умолчанию: Enigma VPN)
2. **Telegram Bot Token** — создать через [@BotFather](https://t.me/BotFather):
   - `/newbot` → имя и username бота
   - прислать token вида `7123456789:AAH...`
3. **Telegram ID админа** — узнать через [@userinfobot](https://t.me/userinfobot), нужен для admin-команд
4. **Домен** — есть ли уже домен? Какой? (например `enigma-vpn.ru`)
5. **Платёжная система** — какую использовать?
   - ЮKassa (нужно ИП/ООО)
   - Crypto Pay (@CryptoBot — нужен token)
   - Telegram Stars (ничего не нужно, но комиссия)
   - YooMoney (token + номер кошелька)
   - Пока без оплаты (только пробный период) — для тестирования
6. **VPN-панель** — Marzban уже установлен?
   - Если да: URL панели, логин, пароль
   - Если нет: есть ли VPS для установки? (IP, root-доступ или «установлю сам по инструкции»)

### 🟡 Нужно для production-деплоя

7. **VPS для backend** — IP, OS (Ubuntu 22.04+), SSH-доступ или «деплою сам по DEPLOY.md»
8. **VPS для VPN-нод** — сколько серверов, в каких странах, IP-адреса
9. **SSL** — Let's Encrypt (автоматически через certbot) или свои сертификаты
10. **DNS** — A-записи: `@`, `api.`, `sub.` → IP backend-сервера
11. **Секреты платёжки:**
    - ЮKassa: `shopId` + `secretKey` из личного кабинета
    - Crypto Pay: API Token из @CryptoBot → Crypto Pay → Apps
    - YooMoney: OAuth token + номер кошелька
12. **Тарифы и цены** — таблица тарифов (название, срок, трафик, цена в ₽)
13. **Пробный период** — включить? Сколько дней / GB?
14. **Юридическое** — тексты оферты и privacy policy (или «сгенерируй шаблон»)

### 🟢 Опционально

15. **Provider ID от Happ** — для брендинга в приложении
16. **Telegram-канал поддержки** — @username
17. **Реферальная программа** — нужна ли (бонус за приглашение)?
18. **Telegram Mini App** — нужен или достаточно бота + сайта?
19. **Логотип / цвета бренда** — для сайта

### Формат запроса

Выведи владельцу сообщение вида:

```
Привет! Чтобы начать разработку Enigma_PN, мне нужна информация от тебя.

Заполни, пожалуйста, что можешь (остальное поставлю заглушками):

1. Бренд: ___
2. Telegram Bot Token: ___
3. Твой Telegram ID: ___
4. Домен: ___ (или «пока нет»)
5. Платежи: ___ (yookassa / cryptopay / stars / yoomoney / пока без оплаты)
6. Marzban: ___ (уже есть / нужна инструкция по установке)
7. Тарифы:
   - 1 мес: ___ ₽, ___ GB, ___ устройств
   - 3 мес: ___ ₽, ...
8. Пробный период: да/нет, ___ дней

Если чего-то нет — напиши «позже», я сделаю mock и инструкцию что донастроить.
```

---

## Порядок реализации

1. **Scaffold** — структура репо, Docker Compose (postgres, redis, api, bot, web, nginx)
2. **Database** — модели, Alembic миграции, seed тарифов
3. **Backend API** — auth, plans, orders, subscription proxy (mock Marzban)
4. **Telegram Bot** — /start, /plans, /mysub, пробный период
5. **Marzban integration** — provisioning service, реальное создание клиентов
6. **Payments** — выбранный провайдер + webhook
7. **Web** — лендинг + dashboard + страница оплаты
8. **Cron/Workers** — expire, reminders, health checks
9. **Admin** — базовая панель или admin-команды в боте
10. **Docs** — DEPLOY.md, USER_SETUP_CHECKLIST.md
11. **Tests** — критичные unit/integration тests (payments idempotency, sub proxy auth)

---

## Требования к качеству

- **Type hints** везде в Python
- **Pydantic v2** для схем
- **Structured logging** (structlog или loguru)
- **Graceful shutdown** для bot и workers
- **Rate limiting** на `/s/{token}` и auth endpoints
- **Secrets** только через env, никогда в коде
- **Idempotent webhooks** — тест обязателен
- **README** на русском с quick start
- **Коммиты** — conventional commits (`feat:`, `fix:`, `docs:`)

---

## MVP Scope (что входит в первую версию)

✅ Telegram-бот: регистрация, пробный, покупка, моя подписка, Happ deep link  
✅ Subscription proxy с проверкой срока  
✅ Marzban provisioning (create / disable / extend)  
✅ Один платёжный провайдер (на выбор владельца)  
✅ PostgreSQL + Redis + Docker Compose  
✅ Базовый лендинг (Next.js)  
✅ `.env.example` + DEPLOY.md  
✅ Cron: expire subscriptions  

❌ Не в MVP (можно TODO):
- Telegram Mini App
- Реферальная система
- Мульти-язычность
- iOS/Android native apps
- Сложная admin-панель (достаточно bot admin commands)
- Автоматический failover нод

---

## Деплой (опиши в DEPLOY.md)

### Минимальный production

1. VPS #1 (4 GB RAM): backend + bot + postgres + redis + nginx
2. VPS #2+ : Marzban node(s) с Xray VLESS Reality
3. DNS: A-records → VPS #1
4. `docker compose -f docker-compose.prod.yml up -d`
5. `certbot certonly --nginx -d domain -d api.domain -d sub.domain`
6. Marzban: создать admin, настроить inbound VLESS Reality
7. Заполнить `.env`, перезапустить
8. Проверить: бот /start → trial → Happ import → connect

---

## Безопасность

- Marzban panel **не публична** — firewall, только admin IP или VPN
- SSH — key-only
- Subscription token — `secrets.token_urlsafe(32)`, не UUID пользователя
- Webhook signatures — verify для каждого провайдера
- SQL injection / XSS — ORM + React escaping
- Rate limit subscription endpoint: 60 req/min per token
- Не логировать subscription URL и payment secrets

---

## Не делай

- ❌ Не хардкодь секреты
- ❌ Не отдавай прямой Marzban subscription URL пользователю
- ❌ Не используй HTTP без SSL для subscription endpoint
- ❌ Не блокируй event loop синхронными вызовами в async коде
- ❌ Не начинай с микросервисов — monorepo + Docker Compose достаточно
- ❌ Не добавляй Kubernetes в MVP

---

## Референсы (изучи при необходимости)

- Marzban: https://github.com/Gozargah/Marzban
- Happ dev docs: https://www.happ.su/main/ru/dev-docs.md
- aiogram 3: https://docs.aiogram.dev/
- Open-source боты (как референс, не копируй слепо):
  - https://github.com/nGrUnD/vpn_tg_bot_template
  - https://github.com/Tarasusrus/3xui-shop

---

## Критерии готовности (Definition of Done)

Проект считается готовым к передаче владельцу, когда:

1. `docker compose up` поднимает все сервисы локально
2. Бот отвечает на `/start`, выдаёт пробный период
3. Subscription URL открывается в Happ и показывает серверы
4. Оплата (или mock) активирует подписку
5. По истечении срока cron отключает доступ
6. `.env.example` полный, DEPLOY.md понятный
7. Владельцу выдан **USER_SETUP_CHECKLIST.md** — что ему настроить на VPS, в DNS, в BotFather, в платёжке

---

**Начни с опросника владельца. Затем — scaffold и код.**
