# NOVICE — парсер дешёвых Telegram NFT от новичков

Mini App + API: ищет **самые дешёвые** NFT-подарки на маркетах Telegram и оставляет лоты от обычных людей.

**Фильтры по умолчанию:**
- уровень аккаунта продавца **≤ 1**
- у продавца **не больше 2 NFT**
- **не перекуп**

Источники: **MRKT**, **Portals**, **Tonnel** (+ demo без токенов).

## Запуск за 1 минуту (demo)

Нужен только **Python 3.11+** (Node не обязателен).

```powershell
cd C:\Users\REALLY\OneDrive\Desktop\parser
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --reload --app-dir backend --port 8000
```

Открой: http://localhost:8000

Сразу увидишь демо-лоты новичков и свой интерфейс Mini App.

## Что нужно поставить

| Что | Зачем | Обязательно? |
|---|---|---|
| Python 3.11+ | весь проект | да |
| `BOT_TOKEN` от [@BotFather](https://t.me/BotFather) | кнопка Mini App в Telegram | для Telegram |
| HTTPS (ngrok / Cloudflare) | Telegram открывает только https | для Telegram |
| `MRKT_TOKEN` / `PORTALS_TOKEN` / `TONNEL_AUTH` | живой парсинг маркетов | для боя |
| `TG_API_ID` + `TG_API_HASH` с my.telegram.org | авто-получение токенов | опционально |

**Отдельные Cursor-плагины / MCP для NFT ставить не нужно.**  
Браузерный MCP в Cursor уже есть — им можно смотреть UI.

## Боевой режим

1. Заполни `.env`:

```env
DEMO_MODE=false
MRKT_TOKEN=...
PORTALS_TOKEN=tma ...
TONNEL_AUTH=...
BOT_TOKEN=123:ABC
WEBAPP_URL=https://your-https-url
```

2. Как взять токены вручную:
   - открой Web Telegram → маркет (MRKT / Portals)
   - F12 → Network
   - найди auth / api запрос
   - скопируй `Authorization` или token из Response

3. Авто-токены (опционально):

```powershell
pip install pyrogram curl_cffi
python backend\tools\fetch_market_tokens.py
```

> На Windows для `tgcrypto` иногда нужны Visual C++ Build Tools. Можно обойтись без него — Pyrogram всё равно работает медленнее.

## Бот Mini App

```powershell
python backend\bot.py
```

Перед этим:
1. Создай бота в BotFather
2. `/newapp` → укажи HTTPS URL (тот же, что в `WEBAPP_URL`)
3. Для локалки подними туннель, например ngrok: `ngrok http 8000`

## API

- `GET /api/health`
- `GET /api/search?max_seller_level=1&max_seller_nfts=2&only_novice=true&max_price_ton=5`

## Структура

```
parser/
  backend/app/          # FastAPI + фильтры + адаптеры источников
  backend/bot.py        # Telegram-бот
  backend/tools/        # получение токенов маркетов
  web/                  # интерфейс Mini App (HTML/CSS/JS)
  frontend/             # опциональный React-вариант (если поставишь Node)
  .env                  # секреты
```

## Важно

Маркеты по-разному отдают `level` / `nft_count`. Фильтр режет явных перекупов и повышает score новичкам. Когда подключим твои живые токены — подстроим маппинг полей под реальный JSON ответа.
