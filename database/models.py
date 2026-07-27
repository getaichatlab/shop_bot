"""Database schema.

Storage: SQLite via aiosqlite (rule 3.5 — small/simple bot).
Swapping to PostgreSQL means replacing database/queries.py only; handlers never
touch SQL directly.

All timestamps are stored in UTC and converted to the display timezone by
utils.formatters (rule 3.5).

Personal data stored (rule 3.2.7 — minimal set, documented):
  users.tg_id       Telegram user id           — required to message the customer
  users.username    Telegram @username         — support/identification
  users.full_name   Telegram profile name      — greeting and order matching
  orders.name       name typed by the customer — delivery
  orders.phone      phone typed by the customer— delivery contact
  orders.address    delivery address           — delivery
No payment card data is ever stored: Telegram Payments handles it end to end.
"""

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Bot users. One row per Telegram account that pressed /start.
-- `language` holds the interface locale code ('uz', 'ru', ...).
-- `currency` is the display currency; money is always *stored* in the base one.
CREATE TABLE IF NOT EXISTS users (
    tg_id       INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    -- Delivery profile: asked once, reused on every later order.
    order_name  TEXT,
    phone       TEXT,
    language    TEXT     NOT NULL DEFAULT 'ru',
    currency    TEXT     NOT NULL DEFAULT 'UZS',
    is_active   INTEGER  NOT NULL DEFAULT 1,   -- 0 = blocked the bot
    created_at  TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now')),
    last_seen   TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Product categories shown on the first catalog screen.
CREATE TABLE IF NOT EXISTS categories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT NOT NULL UNIQUE
);

-- Products. `is_active = 0` is a soft delete so old orders stay readable.
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    title        TEXT    NOT NULL,
    description  TEXT    NOT NULL DEFAULT '',
    price        INTEGER NOT NULL CHECK (price > 0),
    photo_id     TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Live shopping cart. Cleared once the order is created.
CREATE TABLE IF NOT EXISTS cart (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE(user_id, product_id)
);

-- Orders. `total` is computed server-side from product prices, never from the client.
-- Orders. `total` is always in the BASE currency and is the source of truth for
-- payment. `display_currency` / `display_total` record what the customer
-- actually saw, so a later rate change cannot rewrite their history.
CREATE TABLE IF NOT EXISTS orders (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    name             TEXT    NOT NULL,
    phone            TEXT    NOT NULL,
    address          TEXT    NOT NULL,
    comment          TEXT    NOT NULL DEFAULT '',
    total            INTEGER NOT NULL CHECK (total >= 0),
    display_currency TEXT    NOT NULL DEFAULT 'UZS',
    display_total    INTEGER,
    status           TEXT    NOT NULL DEFAULT 'new',
    is_paid          INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Order lines. Title and price are denormalised on purpose: an order must keep
-- the price it was placed at, even if the product changes later.
CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL,
    title       TEXT    NOT NULL,
    price       INTEGER NOT NULL,
    quantity    INTEGER NOT NULL
);

-- Payment ledger. `charge_id` is UNIQUE so a retried callback cannot
-- credit the same payment twice (rule 3.12 — idempotency).
CREATE TABLE IF NOT EXISTS payments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id          INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL,
    amount            INTEGER NOT NULL,
    currency          TEXT    NOT NULL,
    charge_id         TEXT    NOT NULL UNIQUE,
    provider_charge_id TEXT,
    created_at        TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Localized catalog text. The base row (categories.title, products.title,
-- products.description) always holds the DEFAULT_LANG value and acts as the
-- fallback; this table holds one row per additional language.
--
-- A generic (entity, field) shape means adding a third language never requires
-- a schema change.
CREATE TABLE IF NOT EXISTS translations (
    entity     TEXT    NOT NULL,   -- 'category' | 'product'
    entity_id  INTEGER NOT NULL,
    lang       TEXT    NOT NULL,   -- 'uz' | 'ru' | ...
    field      TEXT    NOT NULL,   -- 'title' | 'description'
    value      TEXT    NOT NULL,
    PRIMARY KEY (entity, entity_id, lang, field)
);

-- Exchange rates, expressed as base-currency units per ONE unit of `code`.
-- With UZS as base, USD -> 12101.84 means one dollar costs 12 101.84 so'm.
-- `source` records where the number came from: the central bank API or an admin.
CREATE TABLE IF NOT EXISTS exchange_rates (
    code        TEXT PRIMARY KEY,
    rate        REAL NOT NULL CHECK (rate > 0),
    source      TEXT NOT NULL DEFAULT 'api',   -- 'api' | 'manual'
    updated_at  TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Optional exact price per currency, in that currency's minor units
-- (so'm for UZS, rubles for RUB, cents for USD).
-- A product without a row here is converted from the base price using the rate,
-- which is what makes "$99 exactly, everything else automatic" possible.
CREATE TABLE IF NOT EXISTS product_prices (
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    currency    TEXT    NOT NULL,
    amount      INTEGER NOT NULL CHECK (amount > 0),
    PRIMARY KEY (product_id, currency)
);

-- Manual transfers awaiting review: the customer sent a receipt photo and an
-- admin has to approve or reject it. One open request per order at a time.
CREATE TABLE IF NOT EXISTS payment_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL,
    method      TEXT    NOT NULL,          -- provider code: card_uz, sbp, sber
    receipt_id  TEXT    NOT NULL,          -- Telegram file_id of the photo
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending|approved|rejected
    created_at  TIMESTAMP NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%SZ','now')),
    reviewed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_preq_order  ON payment_requests(order_id);
CREATE INDEX IF NOT EXISTS idx_preq_status ON payment_requests(status);
CREATE INDEX IF NOT EXISTS idx_tr_lookup ON translations(entity, entity_id, lang);
CREATE INDEX IF NOT EXISTS idx_cart_user     ON cart(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_prod_cat      ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_items_order   ON order_items(order_id);
"""

# Demo catalog inserted on first run so the bot is never empty.
# Every text carries a value for each shipped language.
DEMO_CATALOG: list[dict] = [
    {
        "title": {"uz": "Smartfonlar", "ru": "Смартфоны"},
        "products": [
            {
                "title": {"uz": "iPhone 15 128GB", "ru": "iPhone 15 128GB"},
                "description": {
                    "uz": "Yangi, kafolat 1 yil, original quti bilan",
                    "ru": "Новый, гарантия 1 год, оригинальная коробка",
                },
                "price": 11_500_000,
            },
            {
                "title": {"uz": "Samsung Galaxy S24", "ru": "Samsung Galaxy S24"},
                "description": {
                    "uz": "256GB, Snapdragon 8 Gen 3, kafolat",
                    "ru": "256 ГБ, Snapdragon 8 Gen 3, гарантия",
                },
                "price": 9_800_000,
            },
            {
                "title": {"uz": "Xiaomi Redmi Note 13", "ru": "Xiaomi Redmi Note 13"},
                "description": {
                    "uz": "8/256GB, 108MP kamera",
                    "ru": "8/256 ГБ, камера 108 Мп",
                },
                "price": 3_200_000,
            },
        ],
    },
    {
        "title": {"uz": "Noutbuklar", "ru": "Ноутбуки"},
        "products": [
            {
                "title": {"uz": "MacBook Air M2", "ru": "MacBook Air M2"},
                "description": {
                    "uz": '13", 8/256GB, kafolat 1 yil',
                    "ru": '13", 8/256 ГБ, гарантия 1 год',
                },
                "price": 14_900_000,
            },
            {
                "title": {"uz": "Lenovo IdeaPad 3", "ru": "Lenovo IdeaPad 3"},
                "description": {
                    "uz": "Ryzen 5, 16/512GB, FullHD ekran",
                    "ru": "Ryzen 5, 16/512 ГБ, экран FullHD",
                },
                "price": 6_400_000,
            },
        ],
    },
    {
        "title": {"uz": "Aksessuarlar", "ru": "Аксессуары"},
        "products": [
            {
                "title": {"uz": "AirPods Pro 2", "ru": "AirPods Pro 2"},
                "description": {
                    "uz": "Original, faol shovqin bostirish",
                    "ru": "Оригинал, активное шумоподавление",
                },
                "price": 2_700_000,
            },
            {
                "title": {"uz": "Anker 20000mAh", "ru": "Anker 20000 мА·ч"},
                "description": {
                    "uz": "Powerbank, tez quvvatlash 22.5W",
                    "ru": "Повербанк, быстрая зарядка 22.5 Вт",
                },
                "price": 450_000,
            },
            {
                "title": {"uz": "Logitech MX Master 3S", "ru": "Logitech MX Master 3S"},
                "description": {
                    "uz": "Simsiz sichqoncha, 8000 DPI",
                    "ru": "Беспроводная мышь, 8000 DPI",
                },
                "price": 1_150_000,
            },
        ],
    },
]
