# Happ Integration — Enigma_PN

## Subscription URL

Пользователь получает:

```
https://sub.bigwinzone.ru/s/{opaque_token}
```

Endpoint: `GET /s/{token}` в API.

## Headers

- `profile-title: base64:...` — название профиля (Enigma_PN)
- `subscription-userinfo: upload=...; download=...; total=...; expire=...`
- `profile-update-interval: 12`
- опционально `provider-id` из `HAPP_PROVIDER_ID`

## Deep link

```
happ://import/{urlencoded_subscription_url}
```

Кнопка в боте: «Добавить в Happ».

## Import вручную

Happ → `+` → Import from URL → вставить subscription URL.

## Docs

- https://www.happ.su/main/ru/dev-docs.md
- HWID: https://www.happ.su/main/ru/dev-docs/hwid-ssylki.md
- Routing: https://www.happ.su/main/ru/dev-docs/routing.md
- Provider ID: https://www.happ.su/main/ru/dev-docs/provider-id.md

Код: `apps/api/app/services/happ.py`, `apps/api/app/routers/subscription.py`.
