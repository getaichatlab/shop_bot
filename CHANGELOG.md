# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/).

## [1.5.1] — 2026-07-27

### Fixed

- **A freshly booted machine suppressed its own first events.** `time.monotonic()`
  counts from boot, so on a server that just came up it returns a small number.
  Four places used `0.0` as the "this has never happened" default, which then
  read as *"it happened a moment ago"* and skipped the action:
  - `utils/notifier.alert_admins` — the **first admin alert after a deploy was
    silently dropped**, which is the alert that matters most;
  - `services.rates.RateProvider.invalidate()` — the cache was not actually
    invalidated, so a stale exchange rate kept being served;
  - `middlewares/activity` — nobody was recorded in `last_seen` for the first
    five minutes of uptime;
  - `middlewares/throttling` — a first-ever message could be rate-limited.

  All four now use `utils.timing.NEVER` (`-inf`), which is older than any
  monotonic reading on any machine.

  Found by CI: GitHub runners boot seconds before the suite starts, so they
  exposed what a developer machine with days of uptime never could.

### Added

- `utils/timing.py` — the `NEVER` sentinel and the reasoning behind it.
- `tests/test_fresh_boot.py` — seven tests that pin the clock to a just-booted
  machine. Reverting any of the four fixes fails five of them.

---

## [1.5.0] — 2026-07-26

Prepared for a **public** GitHub repository and a publicly reachable demo.

### Security

- Shipped transfer requisites are now impossible on purpose:
  `0000 0000 0000 0000`, `+0 000 000-00-00`, holder `DEMO ACCOUNT`. The previous
  placeholders looked like a real card and carried a personal name — on a public
  demo somebody could have sent money to them.
- In demo mode the transfer screen carries a loud "these requisites are not
  real, do not send money" warning above the receipt request.
- `MAX_OPEN_ORDERS` caps how many unfinished orders one account can pile up, so
  a public bot cannot have its database filled by clicking.
- `.gitignore` hardened: `.env.*`, certificates, `secrets.*`, `credentials.*`,
  `backups/`, `*.sql`, coverage and build artefacts.

### Added

- `SECURITY.md`: how to report a vulnerability, what is and is not committed,
  the enforced security properties with the file that implements each, the known
  limitations, and exactly what personal data is stored.
- `.github/workflows/tests.yml`: runs the suite on Python 3.11 and 3.12, and
  fails the build if a bot token or a tracked `.env` ever appears in the tree.
- `tests/test_public_safety.py`: no committed token, `.gitignore` coverage,
  impossible demo requisites, no personal name in them, the demo warning being
  shown, the open-order cap holding and freeing a slot when an order closes, and
  a stranger getting nothing from any admin surface.
- `PUSH_CHECKLIST.md`: step-by-step publication checklist, including token
  rotation and what to do if a secret is ever committed.
- README badges, a live-demo line and a screenshots section.

### Testing

- 283 → 294 tests.

## [1.4.1] — 2026-07-26

### Fixed

- **A receipt sent as a file was rejected as text.** Telegram delivers a
  compressed picture as `photo` but a dragged-in screenshot as `document`, and
  only `photo` was handled — so the customer saw "please send a photo" while
  looking at the image they had just sent. Both are accepted now. A PDF is still
  refused, with an explanation, because an admin cannot read it at a glance. A
  document is forwarded to the admin as a document: a `file_id` keeps its type.

### Added

- **Name and phone are asked once.** They are stored on the user after the first
  successful order; a returning customer goes straight to the address with the
  saved details shown and a "change name/phone" button. Retyping a phone number
  on every order is the fastest way to lose a sale.
- The profile is saved only after the order is created, so abandoning checkout
  halfway leaves nothing behind.
- `tests/test_persistence.py`: the cart and its quantities surviving a restart,
  carts not leaking between users, the profile being saved, reused, survivable
  and editable, and receipts arriving as photo, as file, or as an unreadable PDF.

### Note

The cart was already stored in the database and always survived a restart —
what wipes it is deleting `shop.db`, which earlier instructions asked for after
each schema change. The new tests pin that behaviour down so it cannot regress.

## [1.4.0] — 2026-07-26

A demo has to answer one question for a prospective client: *can this developer
integrate the payment method I use?* Offering only Telegram Stars answered "no"
for a shop owner in Tashkent or Moscow. Eight methods now, grouped by market.

### Added

- **Payment provider registry** (`payments/providers.py`). Each method declares
  its kind, its market and its requisites; handlers dispatch on that instead of
  branching on names. A ninth method is one entry plus two locale strings.
- **Uzbekistan:** 💙 Payme, 💚 Click, 💳 Humo/Uzcard transfer.
- **CIS:** 🇷🇺 СБП, 🟢 Сбербанк card, 🟣 ЮMoney.
- **Worldwide:** ⭐ Telegram Stars, 💵 cash on delivery.
- **Bank transfer flow — works today, no merchant account.** Requisites are
  shown, the customer sends a photo of the receipt, and it lands in the admin
  chat with Approve / Reject. Approving marks the order paid and notifies the
  customer in their own language.
- The review is a conditional `UPDATE ... WHERE status = 'pending'`, so two
  admins tapping at once cannot both succeed, and a customer tapping the admin
  button changes nothing.
- **Providers without a merchant key still do something useful.** The button
  shows the amount, the order number and a step-by-step description of the live
  flow, states plainly that the key is not connected, and offers the transfer
  route — which completes. Add `PAYME_TOKEN` and the same button opens a real
  payment window, no code change.
- `PAYMENT_METHODS` in `.env` narrows the list per shop.
- Requisites configurable via `CARD_UZ_NUMBER`, `SBP_PHONE`, `SBER_CARD` and
  friends, with placeholders so a fresh demo screen is never blank.
- `payment_requests` table recording every manual transfer and its review.

### Changed

- `PayCB.method` is now a provider code rather than a three-value enum.
- The payment keyboard groups by market, so a Russian customer is not made to
  scroll past Uzbek-only methods to reach СБП.
- Receipt approve/reject labels were renamed so no two buttons in one locale
  share a label — the locale suite enforces that.

### Testing

- 246 → 269 tests. New suite covers the registry, every button appearing and
  being translated, `PAYMENT_METHODS` narrowing, the requisites screen (card for
  Payme-region, phone for СБП), the receipt flow end to end, double-review
  protection, a customer trying to approve their own receipt, the demo
  walkthrough and its fallback, and a configured key switching Payme to a real
  invoice.

## [1.3.0] — 2026-07-26

Aimed at one thing: making this deployable as a public portfolio demo that a
prospective client can evaluate end to end, on free hosting.

### Added

- **Telegram Stars payments.** No merchant account, no provider token, no
  registered business — the only method a public demo can let a stranger
  actually complete. Payme and Click still work when a token is configured.
- `PAYMENT_MODE=demo` issues a token Stars charge and states so on screen next
  to the real order total; `live` charges the full converted amount. A demo that
  quietly billed a token amount while displaying the full price would be a lie
  on screen.
- `utils/stars.py`: base currency → USD → Stars, rounded up. Returns nothing
  rather than inventing a price when the USD rate is unknown.
- Stars amounts are recomputed server-side at pre-checkout, so a tampered
  invoice is refused exactly like a card payment.
- **`storage/sqlite_storage.py`** — FSM state in the same database file. A
  customer halfway through checkout keeps their name and phone across a restart,
  with no Redis and no extra service. This is now the default; Redis still wins
  when `REDIS_URL` is set. Abandoned flows are swept after 7 days.
- `koyeb.yaml` and a Koyeb deployment guide: free tier, no sleep, no card.

### Testing

- 206 → 246 tests. The manual checklist shrank: photo upload (largest size
  stored, photo card rendered, photo at the wrong step rejected), delivery to a
  group chat instead of admin DMs, main/admin keyboard layouts, the one-tap
  contact button, throttling a burst, admins exempt from throttling, and the
  per-language command menu are all automated now.
- New suites for Stars pricing and flow, and for the SQLite FSM storage
  including restart survival, user isolation, unicode and corrupt rows.

## [1.2.1] — 2026-07-26

### Security

- **The bot token could reach an admin chat.** Exception messages often embed
  the API URL, which contains the token. Log records were redacted, but the
  Telegram alert built from the same text was not. `redact_secrets()` is now
  applied to every admin alert as well as to the log.

### Fixed

- `TelegramNetworkError` is treated as transient. A dropped connection to
  api.telegram.org — flaky link, VPN, DNS hiccup — no longer shows the customer
  an error message or wakes the admin; it is logged and aiogram retries. Alerting
  on every network blip trains an admin to ignore the alerts that matter.

### Added

- `tests/test_errors.py`: which failures reach the user, which reach the admin,
  that the alert throttle holds under a loop, and that no secret survives into a
  chat message.

## [1.2.0] — 2026-07-26

### Added

- **Multi-currency display — so'm, rubles and dollars.** Customers switch with
  `/currency` or the 💱 button; the choice is stored per user and applies to the
  catalog, product cards, the cart and the checkout summary.
- `currencies.py`: a registry declaring each currency's decimals and rounding
  step, with UZS as the accounting currency.
- `utils/money.py`: conversion, rounding and formatting as pure functions.
  Amounts are integers in minor units and conversion uses `Decimal`, so the
  arithmetic is exact and the same code runs in tests and production.
- `services/rates.py`: cbu.uz client with an in-memory cache and a background
  refresh every 6 hours. Timeouts, malformed payloads and outages all degrade to
  "keep the last known rates" rather than failing.
- Seed rates so a fresh install can convert before its first successful fetch.
- Admin 💱 **Rates** panel: view rates with their source and timestamp, refresh
  from the API, or type one in by hand.
- A rate set by hand is marked `manual` and is never overwritten by an automatic
  refresh.
- Per-currency product prices: when adding a product the admin can type an exact
  price for each currency, or choose "by rate" and let it follow the exchange
  rate. Pinned prices live in the `product_prices` table.
- Orders now store `display_currency` and `display_total` alongside the base
  total, so a later rate change cannot rewrite a customer's order history.
- Startup warnings for an unsupported `DEFAULT_CURRENCY` and for a `CURRENCY`
  that disagrees with the accounting currency.

### Changed

- Payments remain in so'm — Payme and Click settle in UZS only. When a customer
  has been browsing in another currency the bot states the so'm amount before
  opening the payment window.
- Admin views keep showing the base currency: a group chat has no single user
  currency.
- `CURRENCY_SYMBOL` in `.env` now overrides only the base currency's symbol.
- Locales carry `CURRENCY_SYMBOLS` and `CURRENCY_NAMES` maps instead of one
  scalar symbol.

### Fixed

- `services/__init__.py` re-exported `rates`, shadowing the `services.rates`
  submodule so `import services.rates` returned the provider object instead of
  the module.
- The exchange-rate cache is a module-level singleton and was not cleared between
  tests, letting one test's rates leak into the next after its database was
  deleted.

### Testing

- 108 → 200 tests. New suites cover conversion and rounding, rate parsing from a
  real cbu.uz payload, API failure handling, manual-override precedence, currency
  switching and persistence, pinned prices, cart-total consistency, and the
  base-currency payment path.

## [1.1.2] — 2026-07-26

### Fixed

- **The test suite read the developer's own `.env`.** `load_dotenv()` filled in
  any variable the fixtures had not pinned, so results depended on whose machine
  the suite ran on — a local `CURRENCY_SYMBOL` silently masked the localization
  guard. `tests/conftest.py` now pins every setting the bot reads, and a
  self-check asserts nothing leaked in.

### Added

- Startup configuration warnings: setting `CURRENCY_SYMBOL` while shipping more
  than one language, or pointing `DEFAULT_LANG` at a language that is not
  installed, is now reported in the log at boot.
- `.env.example` explains that `CURRENCY_SYMBOL` overrides every language and
  should stay empty unless the symbol is language-independent (USD, EUR).

## [1.1.1] — 2026-07-26

### Fixed

- **Catalog text ignored the selected language.** With the bot in Russian, the
  inline keyboards still showed Uzbek category and product names, because the
  demo catalog was seeded in one language only. Category names, product names
  and descriptions are now stored per language in a `translations` table and
  resolved for the active locale, with the base row as fallback.
- The currency symbol was hardcoded to `so'm`. It now comes from the active
  locale (`сум` / `so'm`); `CURRENCY_SYMBOL` in `.env` still overrides both.

### Changed

- Adding a category or product asks for the text once per shipped language.
  Adding a third language requires no schema or handler change.
- `get_categories`, `get_products`, `get_product` and `cart_items` take the
  caller's language.

### Added

- `tests/test_language_leak.py`: drives a complete session in each language and
  fails if any word of the other language reaches the screen — message texts,
  captions, reply keyboards and inline button labels alike. Also asserts the
  demo catalog is genuinely translated rather than duplicated.

## [1.1.0] — 2026-07-26

### Added

- **Multilingual interface — Russian and Uzbek.** Users switch with `/language`
  or the 🌐 button; the choice is stored per user and survives restarts.
- `locales/` package with one file per language and a registry that exposes the
  active locale to handlers.
- `I18nMiddleware` resolves the language once per update (database → Telegram
  client language → `DEFAULT_LANG`) and injects it into every handler.
- `Btn` filter matches reply-keyboard buttons by key across all languages, so a
  tap on a stale button from the previous language still reaches its handler.
- `DEFAULT_LANG` setting for new users and admin-facing notifications.
- Telegram command menu is now registered per client language.
- Order-status notifications are delivered in the *customer's* language.
- `tests/test_locales.py`: locale integrity suite — fails the build on a missing
  key, an extra key, a mismatched `{placeholder}`, an empty string, or a
  duplicate button label.

### Changed

- `utils/texts.py` replaced by `locales/uz.py` and `locales/ru.py`.
- All keyboard builders and handlers now take the active locale as an argument
  instead of importing a fixed language.
- `users` table gained a `language` column, applied automatically to existing
  databases by an additive migration on startup.

### Testing

- Test suite grew from 75 to 101: added language switching, persistence across
  restarts, cross-language button handling, a full checkout run in Uzbek, and
  locale integrity checks.

## [1.0.0] — 2026-07-26

First public release.

### Added

**Customer features**
- Catalog browsing: categories → product list → product card with photo
- Shopping cart with quantity controls, per-item removal and clearing
- 4-step checkout (name → phone → address → comment) with confirmation screen
- Phone entry via the Telegram contact button or manual input with validation
- Online payment through Telegram Payments, plus a cash-on-delivery option
- Order history with live status tracking
- Automatic notification whenever an order status changes

**Admin features**
- Category and product creation, with optional product photo
- Recent orders view with one-tap status changes
- `/stats`: total users, active users (7 days), products, orders, paid orders, revenue
- Throttled broadcast to all active users, with a delivery report
- New orders delivered to a dedicated group or privately to each admin

**Architecture and operations**
- Layered structure: `handlers/`, `middlewares/`, `database/`, `keyboards/`, `utils/`, `filters/`
- Typed configuration loaded from `.env`, validated at startup
- Polling and webhook modes behind a single `USE_WEBHOOK` switch
- Graceful shutdown on SIGTERM: FSM storage and HTTP session closed cleanly
- Rotating file logs with a secret-redaction filter
- Docker, docker-compose (with Redis), and Procfile deployment targets
- Automated SQLite backup script with retention

**Security**
- No hardcoded secrets; `.env` is git-ignored
- Admin access enforced by a reusable router-level filter
- Per-user rate limiting middleware
- All callback payloads built and parsed through aiogram CallbackData factories
- Every SQL statement parameterized
- Payment amounts validated server-side at pre-checkout; duplicate charges rejected
  via a `UNIQUE` constraint on `charge_id`
- User-generated content HTML-escaped before rendering
- Webhook mode requires a `secret_token` and uses a non-guessable path

**Reliability**
- Global error handler: friendly Uzbek message to the user, throttled alert to admins
- Explicit handling of blocked users, flood-wait (429), and stale-message edits
- Long messages split automatically at the 4096-character limit
- Broadcasts throttled to 20 messages/second

**Testing**
- 54 unit tests covering validators and formatters
