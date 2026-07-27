# Security

## Reporting a vulnerability

Open a **private** security advisory on GitHub (Security → Report a
vulnerability), or message the maintainer on Telegram. Please do not open a
public issue for anything exploitable.

I aim to reply within a few days.

## What this repository does and does not contain

**Never committed:** `.env`, any bot token, any merchant token, any database
file, any log. All of these are in `.gitignore`, and CI fails the build if a
token or a tracked `.env` shows up.

**Committed on purpose:** the card numbers and phone numbers in
`payments/providers.py` are deliberately impossible placeholders
(`0000 0000 0000 0000`, `+0 000 000-00-00`, holder `DEMO ACCOUNT`). Real
requisites belong in `.env` and never in the repository.

## If you fork or deploy this

1. **Use your own bot token.** Get one from
   [@BotFather](https://t.me/BotFather); never reuse someone else's.
2. **Set `ADMIN_IDS` to your own Telegram id.** Every admin action — product
   creation, order status, broadcast, receipt approval — is gated on it.
3. **Keep `PAYMENT_MODE=demo`** unless you have a merchant account and intend to
   charge real money.
4. **Fill the requisite variables** (`CARD_UZ_NUMBER`, `SBP_PHONE`, …) only when
   you actually want to receive transfers. Until then the demo placeholders and
   the on-screen "do not transfer money" warning protect visitors.
5. **In webhook mode**, `WEBHOOK_SECRET` is mandatory — the bot refuses to start
   without it. Telegram sends it back on every request and the bot verifies it.

## Security properties of the code

These are enforced and covered by tests; a mutation that removes any of them
makes the suite fail.

| Property | Where |
|---|---|
| No secret is hardcoded; all config comes from `.env` | `config.py` |
| Secrets are stripped from logs **and** from admin alerts | `utils/logger.py`, `utils/notifier.py` |
| Every SQL statement is parameterized | `database/queries.py` |
| Admin access is a router-level filter, from config only | `filters/admin.py` |
| `callback_data` is parsed and validated by CallbackData factories | `utils/callbacks.py` |
| Payment amounts are read from the database and re-checked at pre-checkout | `handlers/payment.py` |
| A charge cannot be credited twice (`charge_id` is `UNIQUE`) | `database/models.py` |
| A receipt cannot be approved twice (conditional `UPDATE`) | `database/queries.py` |
| A customer cannot pay, or approve, someone else's order | `handlers/payment.py` |
| User-generated text is HTML-escaped before rendering | `utils/formatters.py` |
| Per-user rate limiting | `middlewares/throttling.py` |
| A capped number of unfinished orders per account | `handlers/order.py` |
| Broadcasts are throttled below Telegram's limits | `utils/broadcast.py` |
| Webhook uses a non-guessable path plus `secret_token` | `config.py`, `bot.py` |

## Known limitations

- **Receipt approval is a human decision.** The bot cannot verify that a
  transfer actually happened; an admin must check the bank before approving.
- **Payme / Click / ЮMoney are untested against live merchant accounts** — the
  code path is tested, the money path is not, because that needs credentials.
- **No refund flow.** Refunds must be handled outside the bot.
- **SQLite is single-writer.** Fine for a shop bot; for heavy concurrency move
  to PostgreSQL (only `database/queries.py` changes) and Redis for FSM.

## Personal data

The bot stores the minimum needed to deliver an order: Telegram id, username,
profile name, the name and phone the customer typed, and the delivery address.
See the docstring at the top of `database/models.py`. **No card data is ever
stored** — Telegram Payments handles it end to end, and manual transfers are
kept only as a Telegram `file_id` pointing at the receipt image.
