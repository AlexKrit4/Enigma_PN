# Архитектура Enigma_PN

См. также корневой AGENT_PROMPT.

```
Telegram Bot / Web
        │
        ▼
   FastAPI API ── Redis/arq workers
        │
        ├─ PostgreSQL (users, plans, orders, subscriptions)
        ├─ YooMoney webhook → activate subscription
        ├─ Marzban API (или mock) → VLESS clients
        └─ GET /s/{token} → Happ subscription body
```

Оплата: YooMoney quickpay + HTTP notification (`sha1_hash`).

Провижининг: после оплаты / trial создаётся user в Marzban, `sub_token` остаётся стабильным.
