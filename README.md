# 🛍 Telegram Shop Bot

[![tests](https://github.com/getaichatlab/shop_bot/actions/workflows/tests.yml/badge.svg)](https://github.com/getaichatlab/shop_bot/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.15-blue)](https://docs.aiogram.dev/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A production-ready Telegram store bot: catalog, cart, checkout, eight payment
methods and a full admin panel — in **Russian and Uzbek**, priced in **so'm,
rubles or dollars**.

Built with **aiogram 3.x** (fully async) and **SQLite**. Runs in polling or
webhook mode without a single code change. **294 tests.**

> **Live demo:** [@your_bot](https://t.me/your_bot) — running in demo mode; the
> payment requisites shown are placeholders and the bot says so on screen.

<!-- Replace @your_bot above with the real bot username after deploying. -->

---

## Screenshots

<!-- Add 4–5 screenshots here after deploying: catalog, product card, cart,
     payment methods, admin order card. They do more for a portfolio than any
     paragraph of description. -->

---

## Features

### For customers

| Feature | Description |
|---|---|
| 🛍 Catalog | Categories → products → product card with photo, description and price |
| 🛒 Cart | Add, increase/decrease quantity, remove a line, clear the cart |
| 📝 Checkout | 4 steps — name → phone → address → comment — with a confirmation screen |
| 📱 Phone entry | One-tap contact button, or typed manually and validated. **Asked once**, then reused |
| 💳 Payment | Payme, Click, Humo/Uzcard transfer, СБП, Сбербанк, ЮMoney, Telegram Stars, cash |
| 📦 Order history | Last 10 orders with their current status |
| 🔔 Notifications | The customer is told automatically when an order status changes |
| 🌐 Languages | Russian and Uzbek — interface **and catalog**. Switchable via `/language`; each user's choice is stored |
| 💱 Currencies | Prices shown in so'm, rubles or dollars. Switchable via `/currency`; rates come from cbu.uz and can be overridden |

### For admins

| Feature | Description |
|---|---|
| ➕ Catalog management | Add categories and products step by step; the name and description are asked once per language, photo optional |
| 📋 Orders | Recent orders with one-tap status changes |
| 📊 Statistics | Users, active users (7 days), products, orders, paid orders, revenue |
| 💱 Rates | View exchange rates, refresh from cbu.uz, or type one in by hand |
| 📣 Broadcast | Send any message to all active users, rate-limited, with a report |
| 🆕 Live alerts | Every new order lands in a group chat or in each admin's DM |

---

## Project structure

```
shop_bot/
├── bot.py                  # entry point: wiring, startup, shutdown
├── config.py               # typed settings, validated on import
├── states.py               # FSM state groups
├── currencies.py           # currency registry: decimals, rounding, base
├── payments/
│   └── providers.py        # payment method registry: kind, region, requisites
├── storage/
│   └── sqlite_storage.py   # FSM state that survives a restart without Redis
├── locales/
│   ├── uz.py               # Uzbek strings
│   ├── ru.py               # Russian strings
│   └── __init__.py         # locale registry + cross-language button lookup
├── services/
│   └── rates.py            # cbu.uz client, cache, background refresh
├── database/
│   ├── models.py           # schema + what personal data is stored and why
│   └── queries.py          # every SQL statement, all parameterized
├── handlers/
│   ├── common.py           # /start, /help, /cancel, /language, contacts
│   ├── catalog.py          # categories, products, product card
│   ├── cart.py             # cart view and quantity changes
│   ├── order.py            # checkout FSM, order history
│   ├── payment.py          # invoices, pre-checkout, successful payment
│   ├── admin.py            # admin panel
│   └── errors.py           # global error handler
├── middlewares/
│   ├── i18n.py             # resolves each user's language, injects it
│   ├── throttling.py       # per-user rate limiting
│   ├── activity.py         # last_seen tracking
│   └── logging_mw.py       # event logging
├── keyboards/
│   ├── reply.py
│   └── inline.py           # all payloads via CallbackData factories
├── utils/
│   ├── money.py            # conversion, rounding, price formatting
│   ├── stars.py            # Telegram Stars pricing
│   ├── validators.py       # pure, unit-tested input validation
│   ├── formatters.py       # money, dates, HTML escaping, message splitting
│   ├── callbacks.py        # CallbackData factories
│   ├── notifier.py         # safe sending, admin alerts
│   ├── broadcast.py        # throttled broadcast queue
│   └── logger.py           # rotating logs + secret redaction
├── filters/
│   ├── admin.py            # reusable IsAdmin filter
│   └── buttons.py          # matches a button in any language
├── scripts/backup.sh       # automated SQLite backup
└── tests/                  # 294 tests (unit, locale, currency, payments, safety, e2e)
```

**Design rule:** handlers hold business logic, SQL lives only in
`database/queries.py`. Moving to PostgreSQL touches that one file.

---

## Requirements

- Python 3.11+
- A bot token from [@BotFather](https://t.me/BotFather)
- Redis (optional — only for high concurrency; SQLite storage is the default)

---

## Setup

### 1. Create the bot

Open [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.

### 2. Find your Telegram ID

Send `/start` to [@userinfobot](https://t.me/userinfobot).

### 3. Install and run

```bash
git clone <repository-url>
cd shop_bot

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# open .env and fill in BOT_TOKEN and ADMIN_IDS

python bot.py
```

On first start the database is created and a demo catalog is seeded
(3 categories, 8 products), so the bot is never empty.

### 4. Run the tests

```bash
pytest -q
```

---

## Configuration

Every setting lives in `.env`. Nothing is hardcoded.

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `BOT_TOKEN` | ✅ | — | Token from @BotFather |
| `ADMIN_IDS` | ✅ | — | Admin Telegram IDs, comma-separated |
| `ORDERS_CHAT_ID` | | empty | Group that receives new orders. Empty → each admin's DM |
| `PAYMENT_METHODS` | | all | Methods to show, comma-separated |
| `PAYME_TOKEN` / `CLICK_TOKEN` / `YOOMONEY_TOKEN` | | empty | Provider tokens. Empty → the button shows a demo walkthrough |
| `CARD_UZ_NUMBER` … `SBER_CARD` | | demo values | Transfer requisites shown to the customer |
| `STARS_ENABLED` | | `true` | Accept Telegram Stars — no merchant account required |
| `PAYMENT_MODE` | | `demo` | `demo` charges a token Stars amount and says so; `live` charges in full |
| `STARS_DEMO_AMOUNT` | | `1` | Stars charged in demo mode |
| `STAR_PRICE_USD` | | `0.02` | Retail price of one Star, used to convert the total |
| `FSM_STORAGE` | | `sqlite` | `sqlite` survives restarts; `memory` does not |
| `CURRENCY` | | `UZS` | ISO currency code |
| `CURRENCY_SYMBOL` | | empty | Overrides the per-language symbol. Empty → `сум` / `so'm` |
| `DB_PATH` | | `shop.db` | SQLite file path |
| `REDIS_URL` | | empty | Redis FSM storage. Overrides `FSM_STORAGE` when set |
| `TIMEZONE` | | `Asia/Tashkent` | Display timezone; data is stored in UTC |
| `DEFAULT_LANG` | | `ru` | Language for new users and admin alerts: `uz` or `ru` |
| `DEFAULT_CURRENCY` | | `UZS` | Display currency for new users: `UZS`, `RUB`, `USD` |
| `THROTTLE_RATE` | | `0.5` | Minimum seconds between two actions per user |
| `MAX_OPEN_ORDERS` | | `10` | Unfinished orders one account may pile up |
| `LOG_LEVEL` | | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `USE_WEBHOOK` | | `false` | `true` switches from polling to webhook |
| `WEBHOOK_BASE_URL` | webhook | — | Public HTTPS URL, no trailing slash |
| `WEBHOOK_SECRET` | webhook | — | 32+ random chars, verified on every request |
| `PORT` | | `8080` | HTTP port in webhook mode |

> **FSM storage:** by default the state lives in the SQLite file next to the
> orders, so a customer who is halfway through checkout keeps their progress
> across a restart — no Redis needed. Set `REDIS_URL` when real concurrency
> arrives; that takes precedence.

---

## Payments

Eight methods, grouped by market so nobody scrolls past another country's
options to reach their own.

| Method | Market | Needs a merchant account? |
|---|---|:---:|
| 💙 **Payme** | 🇺🇿 Uzbekistan | yes |
| 💚 **Click** | 🇺🇿 Uzbekistan | yes |
| 💳 **Humo / Uzcard transfer** | 🇺🇿 Uzbekistan | **no** |
| 🇷🇺 **СБП** | CIS | **no** |
| 🟢 **Сбербанк card** | CIS | **no** |
| 🟣 **ЮMoney** | CIS | yes |
| ⭐ **Telegram Stars** | worldwide | **no** |
| 💵 **Cash on delivery** | — | **no** |

`payments/providers.py` declares each method's kind, market and requisites; the
handlers dispatch on that declaration rather than branching on names. Adding a
ninth method is one entry plus two locale strings.

Narrow the list per shop with `PAYMENT_METHODS` in `.env`:

```
PAYMENT_METHODS=payme,click,card_uz,cash
```

### Bank transfer — works today, no merchant account

The customer sees the card number or phone, holder and bank, transfers the
amount, then sends the receipt — **as a compressed photo or as an image file**.
Telegram delivers a dragged-in screenshot as a *document*, not a photo, so both
are accepted; a PDF is refused with an explanation, because an admin cannot
glance at it in the chat. A document is forwarded as a document, since a
`file_id` keeps its type. It lands in the admin chat with
Approve / Reject buttons; approving marks the order paid and tells the customer
in their own language.

The review is a conditional `UPDATE ... WHERE status = 'pending'`, so two admins
tapping at the same moment cannot both succeed. A customer tapping the admin
button changes nothing.

Requisites come from `.env` (`CARD_UZ_NUMBER`, `SBP_PHONE`, `SBER_CARD`, …).
Placeholders are shown when they are empty, so the demo screen is never blank.

### Payme / Click / ЮMoney

Put the token from [@BotFather](https://t.me/BotFather) → `/mybots` → **Payments**
into `PAYME_TOKEN`, `CLICK_TOKEN` or `YOOMONEY_TOKEN`.

**Without a token the button still works.** It shows the amount, the order
number and a step-by-step description of the live flow, ending with a plain note
that the merchant key is not connected — then offers the transfer route, which
does complete. Add the key and the same button opens a real payment window; no
code changes.

Payme and Click settle in so'm only, so a customer browsing in dollars is told
the so'm amount before the payment window opens.

### ⭐ Telegram Stars

Telegram's own unit for digital goods. No merchant account, no token, available
worldwide.

`PAYMENT_MODE=demo` (the default) charges `STARS_DEMO_AMOUNT` Stars and says so
on screen next to the real total. `PAYMENT_MODE=live` charges the full converted
amount: base currency → USD → Stars via `STAR_PRICE_USD`, rounded up. With no
USD rate the bot says so instead of inventing a price.

### Safety

Amounts are read from the database and recomputed at pre-checkout — for Stars as
well as for cards — so a tampered invoice is refused. `payments.charge_id` is
`UNIQUE`, so a retried callback can never credit the same payment twice.

---

## Running in production

### Option A — systemd on a VPS (polling)

```bash
sudo nano /etc/systemd/system/shopbot.service
```

```ini
[Unit]
Description=Telegram Shop Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/shop_bot
ExecStart=/home/ubuntu/shop_bot/venv/bin/python bot.py
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shopbot
journalctl -u shopbot -f
```

### Option B — Docker

```bash
docker compose up -d --build
docker compose logs -f bot
```

`docker-compose.yml` ships with Redis already wired up.

### Option C — Koyeb (free, recommended for a public demo)

Koyeb's free instance **does not sleep**, which is what a Telegram bot needs: a
sleeping app misses the first message and looks broken to whoever is evaluating
it. No credit card, no expiry.

1. Push this repository to GitHub
2. [app.koyeb.com](https://app.koyeb.com) → **Create Service** → GitHub → pick the repo
3. Builder: **Dockerfile**. Region: **Frankfurt**. Instance: **Free**
4. Port **8080**, health check path `/health`
5. Add these environment variables (mark the first three as **Secret**):

```
BOT_TOKEN         = <from @BotFather>
ADMIN_IDS         = <your Telegram id>
WEBHOOK_SECRET    = <openssl rand -hex 24>
WEBHOOK_BASE_URL  = https://<your-app>.koyeb.app
USE_WEBHOOK       = true
PORT              = 8080
PAYMENT_MODE      = demo
```

`WEBHOOK_BASE_URL` only exists after the first deploy: ship once, copy the URL
Koyeb gives you, paste it in, redeploy.

> **The free filesystem is ephemeral.** The SQLite file is recreated on every
> redeploy, so orders placed before a redeploy disappear and the demo catalog
> comes back. For a portfolio demo that is the right trade — the bot is always
> populated and always responsive. For real data, attach a volume or move to
> Postgres.

`koyeb.yaml` in the repository records this configuration.

### Option D — Railway / Render / Fly.io

`Procfile` is included. Set the environment variables in the dashboard.
For webhook mode set `USE_WEBHOOK=true`, `WEBHOOK_BASE_URL=https://<your-app-url>`
and a `WEBHOOK_SECRET` — a `/health` endpoint is exposed for platform health checks.

### Backups

```bash
chmod +x scripts/backup.sh
crontab -e
# 0 3 * * * /home/ubuntu/shop_bot/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1
```

Uses `sqlite3 .backup`, which is safe on a live database, gzips the result and
keeps 14 days by default.

---

## Manual smoke test

Run through this before every release.

**Language**
- [ ] A brand-new user sees the interface in `DEFAULT_LANG`
- [ ] `/language` → picker appears → choosing Uzbek switches every screen
- [ ] The keyboard relabels itself immediately after switching
- [ ] Tapping a button from the *old* language still works
- [ ] Restart the bot → the chosen language is still applied
- [ ] `/start` after switching does not reset the language
- [ ] **Category and product names inside inline buttons change too**
- [ ] Product descriptions change with the language
- [ ] The currency symbol changes (`сум` ↔ `so'm`)
- [ ] Adding a category asks for the name in both languages
- [ ] Adding a product asks for name and description in both languages
- [ ] The new product then appears correctly in both languages

**Currency**
- [ ] `/currency` → picker → choosing USD reprices the whole catalog
- [ ] Product card, cart and checkout summary all use the chosen currency
- [ ] Cart lines add up to the displayed total
- [ ] Switching currency mid-session repaints prices immediately
- [ ] With no rate stored, prices stay in so'm and a warning is shown
- [ ] Admin 💱 Rates → refresh pulls fresh numbers from cbu.uz
- [ ] Typing a rate by hand marks it `manual`
- [ ] A refresh afterwards does **not** overwrite that manual rate
- [ ] Adding a product offers "by rate" and accepts an exact price per currency
- [ ] A pinned price shows exactly as typed, ignoring the rate
- [ ] Ordering in USD still charges in so'm, with the notice shown first
- [ ] Admin order cards show so'm regardless of the customer's currency

**Customer flow**
- [ ] `/start` → welcome message and main menu appear
- [ ] `/start` twice → no duplicate user is created
- [ ] `/help` → command list
- [ ] Catalog → categories → products → product card
- [ ] "Back" from a photo card returns to the product list correctly
- [ ] Add to cart → the alert shows the updated total
- [ ] Cart → ➕ / ➖ update the total; ➖ at quantity 1 removes the line
- [ ] 🗑 removes a line; "Clear cart" empties it
- [ ] Checkout → name shorter than 3 chars is rejected
- [ ] Phone: contact button works; `abc` is rejected; `+998901234567` is accepted
- [ ] Address shorter than 5 chars is rejected
- [ ] Comment: `yo'q` stores an empty comment
- [ ] Confirmation screen shows the correct items, total and contact details
- [ ] "Cancel" at any step returns to the main menu with the cart intact
- [ ] `/cancel` works mid-flow
- [ ] Confirm → order number is shown and the cart is emptied
- [ ] Admin receives the order card immediately
- [ ] Cash payment → status becomes "accepted"
- [ ] Online payment (test provider) → success message and status "paid"
- [ ] Paying the same order twice is refused
- [ ] "My orders" shows the order with the right status and local time

**Admin flow**
- [ ] Admin panel button is visible only to IDs in `ADMIN_IDS`
- [ ] A non-admin sending the admin button text gets no admin response
- [ ] Add category → appears in the catalog
- [ ] Duplicate category name → friendly error, no crash
- [ ] Add product with a photo → card renders with the image
- [ ] Add product with `yo'q` instead of a photo → text-only card
- [ ] Price `abc` and `-500` are both rejected
- [ ] Orders list → status buttons work and the customer is notified
- [ ] `/stats` numbers match reality
- [ ] Broadcast → preview → send → delivery report
- [ ] Broadcast cancel works

**Resilience**
- [ ] Pressing a button rapidly triggers the throttling notice
- [ ] Restarting the bot does not corrupt the database
- [ ] A user who blocked the bot is marked inactive after a broadcast
- [ ] Logs contain no tokens

---

## Troubleshooting

**`BOT_TOKEN is missing`**
`.env` does not exist or is empty. Run `cp .env.example .env` and fill it in.
Check that you are launching from the project directory.

**`ADMIN_IDS is missing`**
Add at least one numeric ID. Get yours from [@userinfobot](https://t.me/userinfobot).
Use the numeric ID, not the `@username`.

**`Unauthorized` on startup**
The token is wrong or the bot was deleted. Re-copy it from @BotFather, with no
extra spaces or quotes.

**`sqlite3.OperationalError: unable to open database file`**
The process cannot write to `DB_PATH`. Use an absolute path and make sure the
directory exists and is writable (`chown` it to the service user in Docker/systemd).

**Webhook receives nothing**
`WEBHOOK_BASE_URL` must be public HTTPS with a valid certificate — Telegram
rejects self-signed ones. Confirm with `getWebhookInfo` and check that the port is
open.

**Admin panel does not appear**
Your ID is not in `ADMIN_IDS`, or the bot was not restarted after editing `.env`.

**Payment button says "not configured"**
`PAYMENT_PROVIDER_TOKEN` is empty. That is the intended cash-only fallback.

---

## What persists

| Data | Where | Survives a restart |
|---|---|:---:|
| Cart contents and quantities | `cart` table | ✅ |
| Name and phone | `users.order_name`, `users.phone` | ✅ |
| Language and currency | `users` table | ✅ |
| Half-finished checkout | FSM storage (SQLite by default) | ✅ |
| Orders, payments, receipts | their own tables | ✅ |

**Name and phone are asked once.** A returning customer goes straight to the
address, with the saved details shown and an "change name/phone" button on the
keyboard. Making someone retype their phone on every order is the fastest way to
lose a sale.

They are saved only *after* an order goes through, so abandoning checkout
halfway leaves nothing behind.

> Deleting `shop.db` wipes all of this — that is what the file is. Only delete
> it when you deliberately want a clean demo.

---

## Running a public demo safely

This bot is meant to be deployed where strangers can poke at it. What protects
them, and it:

- **`PAYMENT_MODE=demo`** — the transfer screen carries a loud "these requisites
  are not real, do not send money" warning, and Stars charge a token amount with
  the real total shown next to it.
- **Placeholder requisites** — the shipped card numbers are `0000 0000 0000 0000`
  and the holder is `DEMO ACCOUNT`. Impossible on purpose.
- **`MAX_OPEN_ORDERS`** — one account cannot fill the database by clicking.
- **Per-user throttling** — rapid taps are dropped, admins exempt.
- **Admin actions gated on `ADMIN_IDS`** — a stranger sending the admin button
  text, `/stats` or `/rates` gets nothing back.
- **No secrets in logs or alerts** — redacted in both.

`tests/test_public_safety.py` enforces all of the above, plus that no bot token
is committed and that `.gitignore` covers `.env`, databases, logs and backups.

See [SECURITY.md](SECURITY.md) for the full picture.

---

## Localization

The bot ships with **Russian** and **Uzbek**. A user picks their language with
`/language` or the 🌐 button, and the choice is stored in the database, so it
survives restarts.

New users start in `DEFAULT_LANG`, unless their Telegram client language is one
we support — then that one is used.

### Adding a language

1. Copy `locales/ru.py` to `locales/<code>.py` and translate every value
2. Set `LANG_CODE` and `LANG_NAME` at the top of the new file
3. Import it in `locales/__init__.py` and add it to `LOCALES` and `LANGUAGE_ORDER`
4. Run `pytest tests/test_locales.py`

Step 4 matters: those tests fail if the new file is missing a key, has an extra
key, or breaks a `{placeholder}`, so a half-finished translation cannot ship.

### How handlers stay language-agnostic

The i18n middleware resolves the caller's language once per update and injects
the locale module as `t`. Handlers write `t.WELCOME`, never a literal string.

Reply-keyboard buttons are matched by *key* rather than by text:

```python
@router.message(Btn("BTN_CATALOG"))     # matches 🛍 Каталог and 🛍 Katalog
```

That also means a user who taps a stale button from their previous language
still lands in the right handler.

Notifications sent to a customer use the customer's language; notifications
sent to the admin group use `DEFAULT_LANG`, since a group has no single user.

### Catalog text is data, not interface

Category names, product names and descriptions are **business data**, so the bot
cannot translate them. They live in the `translations` table, one row per
(entity, language, field), with the base row acting as the fallback.

When an admin adds a category or product, the bot asks for the text once per
shipped language. Add a third language and the admin is simply asked a third
time — no schema change.

Prices carry the currency symbol from the active locale (`so'm` / `сум`).
Setting `CURRENCY_SYMBOL` in `.env` overrides every language at once, which is
what you want when selling in USD or EUR.

Order lines snapshot the product name in `DEFAULT_LANG`: an order must keep the
name and price it was placed at, and the admin reading it needs one consistent
language.

`tests/test_language_leak.py` drives a full session in each language and fails
if a single word of the other language reaches the screen — including inline
button labels, where the original bug hid.

---

## Currencies

The bot displays prices in **so'm, rubles or dollars**. A customer switches with
`/currency` or the 💱 button, and the choice is stored per user.

### How money is stored

Everything is kept as an **integer number of minor units** — so'm for UZS,
rubles for RUB, cents for USD. Floats never hold an amount; they appear only
inside a single conversion step, which uses `Decimal` so the rounding is exact.

`UZS` is the **accounting currency**. Product prices, order totals and the
payment invoice all live in it; the other currencies are a display layer.

### Where a displayed price comes from

1. **A price pinned for that currency** — the admin typed it, so it is used as-is.
   This is how you get a clean `$99.00` instead of `$95.03`.
2. **Otherwise, converted** from the base price using the current rate.
3. **If no rate is known**, the base price is shown rather than an error.

Cart lines are converted individually and then summed, so the total always
equals what the customer can add up on screen.

### Exchange rates

Rates are fetched from [cbu.uz](https://cbu.uz) on startup and every 6 hours.
An admin can view them under 💱 **Rates**, refresh them on demand, or type one in.

**A rate an admin sets by hand is marked `manual` and is never overwritten by the
API.** That is deliberate: if you have negotiated your own dollar rate, an
automatic refresh must not quietly undo it.

The API is treated as unreliable — every call is timed out, every error is
swallowed, and the last known rates keep working. A fresh install ships with
approximate seed rates so it can convert before the first successful fetch.

### Payments are always in so'm

Payme and Click settle in UZS only. A customer browsing in dollars still pays in
so'm, and the bot says so explicitly before opening the payment window rather
than surprising them with a different number.

Orders record both figures: `total` in the base currency (what drives payment)
and `display_currency` / `display_total` (what the customer saw). A later rate
change therefore cannot rewrite anyone's order history.

### Adding a currency

Add an entry to `CURRENCIES` in `currencies.py`, list it in `CURRENCY_ORDER`, and
add its symbol and name to `CURRENCY_SYMBOLS` / `CURRENCY_NAMES` in every locale.
`decimals` controls how many digits are shown; `rounding_step` keeps converted
prices from ending in stray digits.

---

## Moving to PostgreSQL

Replace `aiosqlite` with `asyncpg` inside `database/queries.py`:

- `aiosqlite.connect(path)` → `asyncpg.create_pool(dsn)`
- `?` placeholders → `$1`, `$2`, …
- `INTEGER PRIMARY KEY AUTOINCREMENT` → `GENERATED ALWAYS AS IDENTITY`

No other file changes.

---

## Roadmap

- Promo codes and discounts
- Delivery zones with per-zone pricing
- Inline product search
- Multilingual UI (uz / ru / en)
- Order export to Excel
- Telegram Web App storefront

---

## License

See [LICENSE](LICENSE).
