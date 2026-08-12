# Telegram MTProto Proxy — Enigma_PN

Прод: **mtg** Fake-TLS на порту **853**, сайт на **:443** через HAProxy.

## DNS

| Запись | Тип | Значение |
|--------|-----|----------|
| `tg` | **A** | `31.76.245.81` |

## Live layout

| Service | Bind | Notes |
| --- | --- | --- |
| HAProxy → nginx | `:443` → `127.0.0.1:8444` | сайт |
| `enigma-mtg` | `:853` | Fake-TLS `www.google.com` |
| Xray Reality | `:52250` | VPN Happ |

## .env

```env
MTPROTO_ENABLED=true
MTPROTO_HOST=tg.bigwinzone.ru
MTPROTO_PORT=853
MTPROTO_SECRET=ee........
MTPROTO_FAKE_TLS_DOMAIN=www.google.com
```

В боте: удалить старый прокси → **«🔌 Прокси Telegram»** (порт **853**).

## Почему чужой прокси живёт, а FI — нет

`premium.vkcommt.space` → **Россия** (MTS, Пятигорск), пинг ~3 мс.  
Наш VPS → **Финляндия**. TSPU чаще режет Fake-TLS к зарубежным ASN (пинг есть, после коннекта — недоступен).

Если и 853 так же — для Telegram из РФ надёжнее **VPN в Happ**.
