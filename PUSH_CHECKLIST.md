# GitHub'ga yuklashdan oldin — nazorat ro'yxati

Bu fayl siz uchun. Repozitoriyni ochiq qilishdan oldin shu tartibda bajaring.

---

## 0. ⚠️ AVVAL: eski tokenni bekor qiling

`.env` faylingizdagi bot tokeni audit vaqtida ekranga chiqdi. Repozitoriyga
tushmagan, lekin **baribir yangilang** — token bir marta ko'ringan bo'lsa,
uni o'zgartirish eng arzon xavfsizlik choralaridan biri.

1. [@BotFather](https://t.me/BotFather) → `/mybots` → botingiz
2. **API Token** → **Revoke current token**
3. Yangi tokenni `.env` ga yozing

Eski token darhol ishlamay qoladi. Bot boshqa hech narsani yo'qotmaydi.

---

## 1. Toza holatni tekshirish

```bash
cd D:\shop_bot

# Testlar
pytest

# Xavfsizlik testlari alohida
pytest tests/test_public_safety.py -v
```

Hammasi yashil bo'lishi kerak (294 ta).

---

## 2. Keraksiz fayllarni o'chirish

```bash
del shop.db
rmdir /s /q logs
mkdir logs
type nul > logs\.gitkeep
rmdir /s /q __pycache__ .pytest_cache
```

`.env` ni **o'chirmang** — u `.gitignore` da, git ko'rmaydi.

---

## 3. Git

```bash
git init
git add .

# ENG MUHIM QADAM — nima yuklanayotganini ko'zdan kechiring
git status
```

Ro'yxatda **bo'lmasligi kerak**: `.env`, `shop.db`, `logs/bot.log`, `venv/`,
`__pycache__/`.

Agar `.env` ko'rinsa — **to'xtang**, `.gitignore` ni tekshiring.

```bash
git commit -m "Telegram shop bot: catalog, cart, 8 payment methods, uz/ru, multi-currency"
git branch -M main
git remote add origin https://github.com/USERNAME/shop_bot.git
git push -u origin main
```

---

## 4. Push'dan keyin

1. **README dagi ikkita joyni tuzating:**
   - `USERNAME` → GitHub username'ingiz (badge havolasi uchun)
   - `@your_bot` → botingizning haqiqiy nomi

2. **Skrinshotlar qo'shing** — README'da joy tayyorlangan. Portfolio uchun
   4–5 ta rasm har qanday tavsifdan kuchliroq: katalog, mahsulot kartochkasi,
   savat, to'lov usullari, admin buyurtma kartochkasi.

3. **Repository → Settings:**
   - Description: `Telegram shop bot — 8 payment methods, uz/ru, multi-currency, 294 tests`
   - Topics: `telegram-bot`, `aiogram`, `python`, `asyncio`, `sqlite`, `e-commerce`, `payments`
   - **Actions** yoqilganini tekshiring — CI birinchi push'da ishga tushadi

4. **Actions → tests** yashil bo'lishini kuting. Badge shundan keyin ishlaydi.

---

## 5. Agar token tasodifan yuklansa

Git tarixi hech qachon o'z-o'zidan tozalanmaydi. Tartib:

1. **Darhol** @BotFather'da tokenni bekor qiling — bu birinchi va eng muhim qadam
2. Keyin tarixni tozalang:
   ```bash
   pip install git-filter-repo
   git filter-repo --path .env --invert-paths --force
   git push --force
   ```
3. Repozitoriy ochiq bo'lgan bo'lsa, token allaqachon skanerlangan deb hisoblang.
   Bekor qilish — yagona ishonchli chora.

---

## 6. Demo botni ishga tushirish (Koyeb)

README'dagi «Option C — Koyeb» bo'limiga qarang. Qisqacha:

1. GitHub repo → [app.koyeb.com](https://app.koyeb.com) → Create Service
2. Builder: **Dockerfile**, Region: **Frankfurt**, Instance: **Free**
3. Port 8080, health check `/health`
4. Secrets: `BOT_TOKEN`, `ADMIN_IDS`, `WEBHOOK_SECRET`
5. Birinchi deploy'dan keyin URL'ni oling → `WEBHOOK_BASE_URL` ga yozing →
   qayta deploy

`PAYMENT_MODE=demo` qolsin — rekvizitlar soxta va bot buni ekranda aytadi.
