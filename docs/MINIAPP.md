# Telegram Mini App — кабинет + казино дней

URL: `https://bigwinzone.ru/app`  
Кнопка в боте: **«🎰 Кабинет»** + Menu Button.

## Функции

- Подписка, пробный период, устройства
- Тарифы (пакет / безлимит / свой) → ЮMoney
- Казино: слот **3×3**, **5 линий**, ставка **1 день**, RTP **~96%**
- Казино только при **безлимитном трафике** и ≥2 днях остатка

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
