# Manual smoke test

Everything in this list is checked by hand before a release. The automated
suite covers the same ground, but a human sees things a test cannot: a button
that is technically correct and still confusing, a screen that flickers, a
message that reads badly in one language.

→ [Back to the README](../README.md)

---

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
