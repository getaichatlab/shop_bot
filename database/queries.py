"""All SQL lives here. Every query is parameterized (rule 3.2.10).

Handlers import this module and never write SQL themselves, so moving to
PostgreSQL later only touches this file.
"""
from __future__ import annotations

import logging
from typing import Any

import aiosqlite

from config import settings
from currencies import BASE_CURRENCY
from database.models import DEMO_CATALOG, SCHEMA

log = logging.getLogger(__name__)

_UTC_NOW = "STRFTIME('%Y-%m-%dT%H:%M:%SZ','now')"


# ----------------------------------------------------------------- lifecycle

async def init_db() -> None:
    """Create tables, apply lightweight migrations, seed the demo catalog."""
    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()
        await _migrate(conn)

        cur = await conn.execute("SELECT COUNT(*) FROM categories")
        row = await cur.fetchone()
        if row and row[0] == 0:
            await _seed_demo(conn)
            log.info("Demo catalog seeded")


async def _migrate(conn: aiosqlite.Connection) -> None:
    """Additive migrations for databases created by an earlier version.

    `CREATE TABLE IF NOT EXISTS` leaves an existing table untouched, so new
    columns have to be added explicitly.
    """
    cur = await conn.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in await cur.fetchall()}

    if "language" not in columns:
        await conn.execute(
            "ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'ru'"
        )
        await conn.commit()
        log.info("Migration applied: users.language")

    if "currency" not in columns:
        await conn.execute(
            "ALTER TABLE users ADD COLUMN currency TEXT NOT NULL DEFAULT 'UZS'"
        )
        await conn.commit()
        log.info("Migration applied: users.currency")

    if "order_name" not in columns:
        await conn.execute("ALTER TABLE users ADD COLUMN order_name TEXT")
        await conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        await conn.commit()
        log.info("Migration applied: users.order_name, users.phone")

    cur = await conn.execute("PRAGMA table_info(orders)")
    order_columns = {row[1] for row in await cur.fetchall()}

    # The currency the customer saw, and the total as displayed to them.
    # `orders.total` always stays in the base currency.
    if "display_currency" not in order_columns:
        await conn.execute(
            "ALTER TABLE orders ADD COLUMN display_currency TEXT NOT NULL DEFAULT 'UZS'"
        )
        await conn.execute("ALTER TABLE orders ADD COLUMN display_total INTEGER")
        await conn.commit()
        log.info("Migration applied: orders.display_currency, orders.display_total")


async def _seed_demo(conn: aiosqlite.Connection) -> None:
    """Insert the demo catalog together with its translations."""
    base = settings.default_lang

    for category in DEMO_CATALOG:
        titles = category["title"]
        cur = await conn.execute(
            "INSERT INTO categories (title) VALUES (?)",
            (titles.get(base) or next(iter(titles.values())),),
        )
        category_id = cur.lastrowid
        await _insert_translations(conn, "category", category_id, {"title": titles})

        for product in category["products"]:
            p_titles = product["title"]
            p_descriptions = product["description"]
            cur = await conn.execute(
                "INSERT INTO products (category_id, title, description, price) "
                "VALUES (?, ?, ?, ?)",
                (
                    category_id,
                    p_titles.get(base) or next(iter(p_titles.values())),
                    p_descriptions.get(base) or next(iter(p_descriptions.values())),
                    product["price"],
                ),
            )
            await _insert_translations(
                conn,
                "product",
                cur.lastrowid,
                {"title": p_titles, "description": p_descriptions},
            )
    await conn.commit()


async def _insert_translations(
    conn: aiosqlite.Connection,
    entity: str,
    entity_id: int,
    fields: dict[str, dict[str, str]],
) -> None:
    rows = [
        (entity, entity_id, lang, field, value)
        for field, by_lang in fields.items()
        for lang, value in by_lang.items()
        if value
    ]
    if rows:
        await conn.executemany(
            "INSERT OR REPLACE INTO translations "
            "(entity, entity_id, lang, field, value) VALUES (?, ?, ?, ?, ?)",
            rows,
        )


# ----------------------------------------------------------------- helpers

async def _fetchall(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    async with aiosqlite.connect(settings.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(query, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def _fetchone(query: str, params: tuple = ()) -> dict[str, Any] | None:
    rows = await _fetchall(query, params)
    return rows[0] if rows else None


async def _execute(query: str, params: tuple = ()) -> int:
    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        cur = await conn.execute(query, params)
        await conn.commit()
        return cur.lastrowid or 0


# ----------------------------------------------------------------- users

async def upsert_user(
    tg_id: int, username: str | None, full_name: str, language: str | None = None
) -> None:
    """Idempotent: /start can be pressed any number of times (rule 3.6).

    The stored language is never overwritten here — a returning user keeps the
    language they chose.
    """
    await _execute(
        f"""
        INSERT INTO users (tg_id, username, full_name, language)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username  = excluded.username,
            full_name = excluded.full_name,
            is_active = 1,
            last_seen = {_UTC_NOW}
        """,
        (tg_id, username, full_name, language or settings.default_lang),
    )


async def get_user_language(tg_id: int) -> str | None:
    row = await _fetchone("SELECT language FROM users WHERE tg_id = ?", (tg_id,))
    return row["language"] if row else None


async def set_user_language(tg_id: int, language: str) -> None:
    await _execute("UPDATE users SET language = ? WHERE tg_id = ?", (language, tg_id))


async def get_profile(tg_id: int) -> dict | None:
    """The delivery details the customer gave last time, if any."""
    row = await _fetchone(
        "SELECT order_name, phone FROM users WHERE tg_id = ?", (tg_id,)
    )
    if not row or not row["order_name"] or not row["phone"]:
        return None
    return {"name": row["order_name"], "phone": row["phone"]}


async def save_profile(tg_id: int, name: str, phone: str) -> None:
    """Remember the details so the next order does not ask again."""
    await _execute(
        "UPDATE users SET order_name = ?, phone = ? WHERE tg_id = ?",
        (name, phone, tg_id),
    )


async def clear_profile(tg_id: int) -> None:
    await _execute(
        "UPDATE users SET order_name = NULL, phone = NULL WHERE tg_id = ?", (tg_id,)
    )


async def get_user_currency(tg_id: int) -> str | None:
    row = await _fetchone("SELECT currency FROM users WHERE tg_id = ?", (tg_id,))
    return row["currency"] if row else None


async def set_user_currency(tg_id: int, currency: str) -> None:
    await _execute("UPDATE users SET currency = ? WHERE tg_id = ?", (currency, tg_id))


# ----------------------------------------------------------------- rates

async def get_rates() -> dict[str, dict]:
    """All stored rates, keyed by currency code."""
    rows = await _fetchall("SELECT * FROM exchange_rates")
    return {row["code"]: row for row in rows}


async def get_rate(code: str) -> float | None:
    if code == BASE_CURRENCY:
        return 1.0
    row = await _fetchone("SELECT rate FROM exchange_rates WHERE code = ?", (code,))
    return float(row["rate"]) if row else None


async def set_rate(code: str, rate: float, source: str = "manual") -> None:
    await _execute(
        f"""
        INSERT INTO exchange_rates (code, rate, source, updated_at)
        VALUES (?, ?, ?, {_UTC_NOW})
        ON CONFLICT(code) DO UPDATE SET
            rate = excluded.rate,
            source = excluded.source,
            updated_at = {_UTC_NOW}
        """,
        (code, rate, source),
    )


async def set_rates_bulk(rates: dict[str, float], source: str = "api") -> int:
    """Store several rates at once. Returns how many rows were written."""
    if not rates:
        return 0
    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.executemany(
            f"""
            INSERT INTO exchange_rates (code, rate, source, updated_at)
            VALUES (?, ?, ?, {_UTC_NOW})
            ON CONFLICT(code) DO UPDATE SET
                rate = excluded.rate,
                source = excluded.source,
                updated_at = {_UTC_NOW}
            """,
            [(code, rate, source) for code, rate in rates.items()],
        )
        await conn.commit()
    return len(rates)


async def touch_user(tg_id: int) -> None:
    await _execute(
        f"UPDATE users SET last_seen = {_UTC_NOW} WHERE tg_id = ?", (tg_id,)
    )


async def deactivate_user(tg_id: int) -> None:
    """Called when Telegram reports the user blocked the bot."""
    await _execute("UPDATE users SET is_active = 0 WHERE tg_id = ?", (tg_id,))


async def get_active_user_ids() -> list[int]:
    rows = await _fetchall("SELECT tg_id FROM users WHERE is_active = 1")
    return [r["tg_id"] for r in rows]


# ----------------------------------------------------------------- catalog

async def get_categories(lang: str | None = None) -> list[dict]:
    """Categories with the title resolved for `lang`, falling back to the base row."""
    return await _fetchall(
        """
        SELECT c.id,
               COALESCE(tr.value, c.title) AS title
        FROM categories c
        LEFT JOIN translations tr
               ON tr.entity = 'category'
              AND tr.entity_id = c.id
              AND tr.field = 'title'
              AND tr.lang = ?
        ORDER BY title
        """,
        (lang or settings.default_lang,),
    )


async def add_category(titles: dict[str, str]) -> int:
    """`titles` maps a language code to the category name in that language."""
    base = settings.default_lang
    base_title = titles.get(base) or next(iter(titles.values()))

    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        cur = await conn.execute(
            "INSERT INTO categories (title) VALUES (?)", (base_title,)
        )
        category_id = cur.lastrowid
        await _insert_translations(conn, "category", category_id, {"title": titles})
        await conn.commit()
        return category_id


async def category_exists(category_id: int) -> bool:
    row = await _fetchone("SELECT 1 AS ok FROM categories WHERE id = ?", (category_id,))
    return row is not None


# `price` is always the base-currency price. `price_override` is the exact price
# the admin typed for the requested currency, or NULL when it should be computed
# from the exchange rate.
_PRODUCT_SELECT = """
    SELECT p.id,
           p.category_id,
           p.price,
           p.photo_id,
           p.is_active,
           COALESCE(tt.value, p.title)       AS title,
           COALESCE(td.value, p.description) AS description,
           pp.amount                         AS price_override
    FROM products p
    LEFT JOIN translations tt
           ON tt.entity = 'product' AND tt.entity_id = p.id
          AND tt.field = 'title' AND tt.lang = ?
    LEFT JOIN translations td
           ON td.entity = 'product' AND td.entity_id = p.id
          AND td.field = 'description' AND td.lang = ?
    LEFT JOIN product_prices pp
           ON pp.product_id = p.id AND pp.currency = ?
"""


async def get_products(
    category_id: int, lang: str | None = None, currency: str | None = None
) -> list[dict]:
    code = lang or settings.default_lang
    cur = currency or BASE_CURRENCY
    return await _fetchall(
        _PRODUCT_SELECT
        + " WHERE p.category_id = ? AND p.is_active = 1 ORDER BY p.id",
        (code, code, cur, category_id),
    )


async def get_product(
    product_id: int, lang: str | None = None, currency: str | None = None
) -> dict | None:
    code = lang or settings.default_lang
    cur = currency or BASE_CURRENCY
    return await _fetchone(
        _PRODUCT_SELECT + " WHERE p.id = ? AND p.is_active = 1",
        (code, code, cur, product_id),
    )


async def set_product_price(product_id: int, currency: str, amount: int) -> None:
    """Pin an exact price for one currency (minor units)."""
    await _execute(
        "INSERT INTO product_prices (product_id, currency, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(product_id, currency) DO UPDATE SET amount = excluded.amount",
        (product_id, currency, amount),
    )


async def clear_product_price(product_id: int, currency: str) -> None:
    """Drop the pinned price so the value is computed from the rate again."""
    await _execute(
        "DELETE FROM product_prices WHERE product_id = ? AND currency = ?",
        (product_id, currency),
    )


async def get_product_prices(product_id: int) -> dict[str, int]:
    rows = await _fetchall(
        "SELECT currency, amount FROM product_prices WHERE product_id = ?",
        (product_id,),
    )
    return {row["currency"]: row["amount"] for row in rows}


async def add_product(
    category_id: int,
    titles: dict[str, str],
    descriptions: dict[str, str],
    price: int,
    photo_id: str | None,
    prices: dict[str, int] | None = None,
) -> int:
    """`titles` / `descriptions` map a language code to that language's text."""
    base = settings.default_lang
    base_title = titles.get(base) or next(iter(titles.values()))
    base_description = descriptions.get(base, "") if descriptions else ""

    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        cur = await conn.execute(
            "INSERT INTO products (category_id, title, description, price, photo_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (category_id, base_title, base_description, price, photo_id),
        )
        product_id = cur.lastrowid
        await _insert_translations(
            conn,
            "product",
            product_id,
            {"title": titles, "description": descriptions},
        )
        if prices:
            await conn.executemany(
                "INSERT INTO product_prices (product_id, currency, amount) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(product_id, currency) DO UPDATE SET amount = excluded.amount",
                [
                    (product_id, code, amount)
                    for code, amount in prices.items()
                    if code != BASE_CURRENCY and amount
                ],
            )
        await conn.commit()
        return product_id


async def soft_delete_product(product_id: int) -> None:
    await _execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))


# ----------------------------------------------------------------- cart

async def cart_add(user_id: int, product_id: int, qty: int = 1) -> bool:
    """Returns False if the product no longer exists (untrusted callback data)."""
    if not await _fetchone(
        "SELECT 1 AS ok FROM products WHERE id = ? AND is_active = 1", (product_id,)
    ):
        return False
    await _execute(
        """
        INSERT INTO cart (user_id, product_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + ?
        """,
        (user_id, product_id, qty, qty),
    )
    return True


async def cart_set_qty(user_id: int, product_id: int, qty: int) -> None:
    if qty <= 0:
        await cart_remove(user_id, product_id)
        return
    await _execute(
        "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?",
        (qty, user_id, product_id),
    )


async def cart_remove(user_id: int, product_id: int) -> None:
    await _execute(
        "DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id)
    )


async def cart_clear(user_id: int) -> None:
    await _execute("DELETE FROM cart WHERE user_id = ?", (user_id,))


async def cart_items(
    user_id: int, lang: str | None = None, currency: str | None = None
) -> list[dict]:
    code = lang or settings.default_lang
    cur = currency or BASE_CURRENCY
    return await _fetchall(
        """
        SELECT c.product_id,
               c.quantity,
               COALESCE(tt.value, p.title) AS title,
               p.price,
               (c.quantity * p.price) AS subtotal,
               pp.amount                  AS price_override
        FROM cart c
        JOIN products p ON p.id = c.product_id AND p.is_active = 1
        LEFT JOIN translations tt
               ON tt.entity = 'product' AND tt.entity_id = p.id
              AND tt.field = 'title' AND tt.lang = ?
        LEFT JOIN product_prices pp
               ON pp.product_id = p.id AND pp.currency = ?
        WHERE c.user_id = ?
        ORDER BY title
        """,
        (code, cur, user_id),
    )


async def cart_total(user_id: int) -> int:
    row = await _fetchone(
        """
        SELECT COALESCE(SUM(c.quantity * p.price), 0) AS total
        FROM cart c
        JOIN products p ON p.id = c.product_id AND p.is_active = 1
        WHERE c.user_id = ?
        """,
        (user_id,),
    )
    return int(row["total"]) if row else 0


# ----------------------------------------------------------------- orders

async def create_order(
    user_id: int,
    name: str,
    phone: str,
    address: str,
    comment: str,
    display_currency: str = BASE_CURRENCY,
    display_total: int | None = None,
) -> int | None:
    """Create an order from the cart inside a single transaction.

    The total is recomputed from the products table — never taken from the client.

    Item titles are snapshotted in DEFAULT_LANG: an order line must keep the
    name and price it was placed at, and the admin who reads the order needs a
    single consistent language.
    """
    async with aiosqlite.connect(settings.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")

        cur = await conn.execute(
            """
            SELECT c.product_id, c.quantity, p.title, p.price
            FROM cart c
            JOIN products p ON p.id = c.product_id AND p.is_active = 1
            WHERE c.user_id = ?
            """,
            (user_id,),
        )
        items = [dict(r) for r in await cur.fetchall()]
        if not items:
            return None

        total = sum(i["price"] * i["quantity"] for i in items)

        cur = await conn.execute(
            "INSERT INTO orders "
            "(user_id, name, phone, address, comment, total, "
            " display_currency, display_total) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, name, phone, address, comment, total,
                display_currency, display_total,
            ),
        )
        order_id = cur.lastrowid

        await conn.executemany(
            "INSERT INTO order_items (order_id, product_id, title, price, quantity) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (order_id, i["product_id"], i["title"], i["price"], i["quantity"])
                for i in items
            ],
        )
        await conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await conn.commit()
        return order_id


async def get_order(order_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))


async def get_order_items(order_id: int) -> list[dict]:
    return await _fetchall(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    )


async def get_user_orders(user_id: int, limit: int = 10) -> list[dict]:
    return await _fetchall(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )


async def count_open_orders(user_id: int) -> int:
    """Unpaid, unfinished orders. Used to stop a public demo being flooded."""
    row = await _fetchone(
        "SELECT COUNT(*) AS c FROM orders "
        "WHERE user_id = ? AND is_paid = 0 AND status NOT IN ('done', 'canceled')",
        (user_id,),
    )
    return row["c"] if row else 0


async def get_recent_orders(limit: int = 10) -> list[dict]:
    return await _fetchall("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))


async def set_order_status(order_id: int, status: str) -> None:
    await _execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))


# ----------------------------------------------------------------- payments

async def record_payment(
    order_id: int,
    user_id: int,
    amount: int,
    currency: str,
    charge_id: str,
    provider_charge_id: str | None,
) -> bool:
    """Idempotent payment registration.

    Returns True if this is a new payment, False if the same charge_id was
    already processed (duplicate callback / retry).
    """
    async with aiosqlite.connect(settings.db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        try:
            await conn.execute(
                "INSERT INTO payments "
                "(order_id, user_id, amount, currency, charge_id, provider_charge_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (order_id, user_id, amount, currency, charge_id, provider_charge_id),
            )
        except aiosqlite.IntegrityError:
            log.info("Duplicate payment ignored: charge_id=%s", charge_id)
            return False
        await conn.execute(
            "UPDATE orders SET is_paid = 1, status = 'paid' WHERE id = ?", (order_id,)
        )
        await conn.commit()
        return True


# ----------------------------------------------------------------- receipts

async def create_payment_request(
    order_id: int, user_id: int, method: str, receipt_id: str
) -> int:
    return await _execute(
        "INSERT INTO payment_requests (order_id, user_id, method, receipt_id) "
        "VALUES (?, ?, ?, ?)",
        (order_id, user_id, method, receipt_id),
    )


async def get_payment_request(request_id: int) -> dict | None:
    return await _fetchone(
        "SELECT * FROM payment_requests WHERE id = ?", (request_id,)
    )


async def review_payment_request(request_id: int, approved: bool) -> bool:
    """Mark a request reviewed. Returns False if it was already handled.

    The status check is part of the UPDATE, so two admins tapping at the same
    moment cannot both succeed.
    """
    async with aiosqlite.connect(settings.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            f"""
            UPDATE payment_requests
            SET status = ?, reviewed_at = {_UTC_NOW}
            WHERE id = ? AND status = 'pending'
            """,
            ("approved" if approved else "rejected", request_id),
        )
        if cur.rowcount == 0:
            return False

        if approved:
            cur = await conn.execute(
                "SELECT order_id FROM payment_requests WHERE id = ?", (request_id,)
            )
            row = await cur.fetchone()
            if row:
                await conn.execute(
                    "UPDATE orders SET is_paid = 1, status = 'paid' WHERE id = ?",
                    (row["order_id"],),
                )
        await conn.commit()
        return True


# ----------------------------------------------------------------- stats

async def stats() -> dict:
    users = await _fetchone("SELECT COUNT(*) AS c FROM users")
    active = await _fetchone(
        "SELECT COUNT(*) AS c FROM users "
        "WHERE is_active = 1 AND last_seen >= DATETIME('now', '-7 days')"
    )
    products = await _fetchone(
        "SELECT COUNT(*) AS c FROM products WHERE is_active = 1"
    )
    orders = await _fetchone(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS revenue FROM orders"
    )
    paid = await _fetchone("SELECT COUNT(*) AS c FROM orders WHERE is_paid = 1")
    return {
        "users": users["c"] if users else 0,
        "active": active["c"] if active else 0,
        "products": products["c"] if products else 0,
        "orders": orders["c"] if orders else 0,
        "revenue": orders["revenue"] if orders else 0,
        "paid": paid["c"] if paid else 0,
    }
