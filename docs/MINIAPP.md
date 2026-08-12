# Telegram Mini App — кабинет + казино дней

URL: `https://bigwinzone.ru/app`  
Кнопка в боте: **«🎰 Кабинет»** + Menu Button.

## Функции

- Подписка, пробный период, устройства
- Тарифы (пакет / безлимит / свой) → ЮMoney
- Казино: слот **3×3**, **5 линий**, ставка **1 день**, RTP **96%**, hit rate **25%**
- Банк из **30 000 книг** (паттерн + заранее известный результат); за цикл 30 000 ставок возвращается **28 800** дней (RTP 96%)
- **1 из 75** книг — бонус: три «В» → 7 фриспинов с множителем («Х» = +1×); бонусная книга считается как **1 спин** для RTP
- Макс. выигрыш: **365 дней** — ровно **1** книга с полной доской 👑; линия 👑 = **75** дней
- Казино только при **безлимитном трафике** и ≥2 днях остатка

### Таблица выплат (3 в ряд)

| Символ | Дни |
|--------|-----|
| 🍒 | 1 |
| 🍋 | 2 |
| 🔔 | 3 |
| ⭐ | 5 |
| 💎 | 10 |
| 7️⃣ | 15 |
| 👑 | 75 |
| 👑×9 (джекпот) | 365 |

## Env

```env
MINIAPP_URL=https://bigwinzone.ru/app
CASINO_ENABLED=true
NEXT_PUBLIC_API_URL=https://api.bigwinzone.ru
```

## BotFather

В настройках бота укажите домен Web App: `bigwinzone.ru` (или полный URL Mini App).

## API

- `POST /api/v1/miniapp/auth` — `{ init_data }` → JWT
- `POST /api/v1/miniapp/trial|orders|orders/custom`
- `GET /api/v1/miniapp/casino/status`
- `POST /api/v1/miniapp/casino/spin`

## Важно

1. BotFather → Bot Settings → Domain: `bigwinzone.ru`
2. В боте `/start` → кнопка **Кабинет**
3. Казино: только безлимитный тариф, ставка 1 день
