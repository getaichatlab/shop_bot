"""Uzbek locale.

To add a language, copy this file, translate the values and register it in
locales/__init__.py. Every key below must exist in every locale file.
"""
from __future__ import annotations

LANG_CODE = "uz"
LANG_NAME = "🇺🇿 O'zbekcha"


# ----------------------------------------------------------------- common
WELCOME = (
    "Assalomu alaykum, <b>{name}</b>! 👋\n\n"
    "Bu — internet-do'kon boti.\n"
    "Katalogdan mahsulot tanlang, savatga qo'shing va buyurtma bering.\n\n"
    "Quyidagi menyudan boshlang 👇"
)

HELP = (
    "<b>Botdan foydalanish</b>\n\n"
    "🛍 <b>Katalog</b> — mahsulotlarni ko'rish va savatga qo'shish\n"
    "🛒 <b>Savat</b> — miqdorni o'zgartirish, buyurtma berish\n"
    "📦 <b>Buyurtmalarim</b> — buyurtma holatini kuzatish\n"
    "ℹ️ <b>Aloqa</b> — operator bilan bog'lanish\n\n"
    "Tilni almashtirish: /language\n"
    "Bekor qilish uchun istalgan bosqichda /cancel yozing."
)

# ----------------------------------------------------------------- language
CHOOSE_LANGUAGE = "Tilni tanlang:"
LANGUAGE_SET = "✅ Til o'zgartirildi: O'zbekcha"

CONTACTS = (
    "<b>Biz bilan aloqa</b>\n\n"
    "📞 Telefon: +998 90 000 00 00\n"
    "🕐 Ish vaqti: 09:00 – 20:00, dushanba–shanba\n"
    "📍 Manzil: Toshkent shahri\n\n"
    "Savolingiz bo'lsa shu yerga yozing — operator javob beradi."
)

MAIN_MENU = "Asosiy menyu"
CANCELLED = "Bekor qilindi."
NOTHING_TO_CANCEL = "Hozir bekor qiladigan amal yo'q."
LOADING = "⏳ Bir soniya..."
GENERIC_ERROR = (
    "⚠️ Kutilmagan xatolik yuz berdi. Biz bu haqda xabardor bo'ldik.\n"
    "Iltimos, birozdan so'ng qayta urinib ko'ring yoki /start bosing."
)
THROTTLED = "⏳ Juda tez bosyapsiz. Bir soniya kuting."

# ----------------------------------------------------------------- catalog
CHOOSE_CATEGORY = "Kategoriyani tanlang:"
CHOOSE_PRODUCT = "Mahsulotni tanlang:"
CATALOG_EMPTY = "Katalog hozircha bo'sh. Tez orada mahsulotlar qo'shiladi."
CATEGORY_EMPTY = "Bu kategoriyada mahsulot yo'q."
PRODUCT_NOT_FOUND = "Mahsulot topilmadi yoki sotuvdan olingan."
NO_DESCRIPTION = "Tavsif kiritilmagan."

PRODUCT_CARD = (
    "<b>{title}</b>\n\n"
    "{description}\n\n"
    "💰 Narxi: <b>{price}</b>"
)

ADDED_TO_CART = "Savatga qo'shildi ✅\nJami: {total}"

# ----------------------------------------------------------------- cart
CART_EMPTY = "Savatingiz bo'sh 🕸\n\n🛍 Katalog dan mahsulot tanlang."
CART_HEADER = "<b>🛒 Savatingiz</b>\n"
CART_LINE = "• {title}\n   {qty} × {price} = <b>{subtotal}</b>"
CART_TOTAL = "\n<b>Jami: {total}</b>"
CART_CLEARED = "Savat tozalandi 🗑"
ITEM_REMOVED = "O'chirildi"

# ----------------------------------------------------------------- order
ORDER_STEP_NAME = "<b>Buyurtma rasmiylashtirish — 1/4</b>\n\nIsm-familiyangizni yozing:"
ORDER_STEP_PHONE = (
    "<b>2/4</b>\n\nTelefon raqamingizni yuboring.\n"
    "Pastdagi tugmani bosing yoki qo'lda yozing (masalan +998901234567):"
)
ORDER_STEP_ADDRESS = (
    "<b>3/4</b>\n\nYetkazib berish manzilini yozing\n(shahar, ko'cha, uy, xonadon):"
)
ORDER_STEP_COMMENT = (
    "<b>4/4</b>\n\nIzoh qoldirasizmi? (yetkazish vaqti, qo'shimcha talab)\n"
    "Kerak bo'lmasa <b>yo'q</b> deb yozing:"
)

ERR_NAME_SHORT = "Ism juda qisqa. To'liq ism-familiyangizni yozing:"
ERR_NAME_LONG = "Ism juda uzun (maksimum {limit} belgi). Qisqaroq yozing:"
ERR_PHONE_INVALID = (
    "Raqam noto'g'ri. Namuna: <code>+998901234567</code>\nQayta yuboring:"
)
ERR_ADDRESS_SHORT = "Manzil juda qisqa. Aniqroq yozing:"
ERR_ADDRESS_LONG = "Manzil juda uzun (maksimum {limit} belgi). Qisqaroq yozing:"
ERR_COMMENT_LONG = "Izoh juda uzun (maksimum {limit} belgi). Qisqaroq yozing:"
ERR_TEXT_EXPECTED = "Iltimos, matn ko'rinishida yuboring."
ERR_PRICE_INVALID = "Narx faqat raqamlardan iborat bo'lishi kerak. Qayta yozing:"

ORDER_CHECK = "Tekshiring 👇"
ORDER_CONFIRM_HEADER = "<b>Buyurtmangizni tasdiqlang</b>\n"
ORDER_CONFIRM_LINE = "• {title} × {qty} = {subtotal}"
ORDER_CONFIRM_FOOTER = (
    "\n<b>Jami: {total}</b>\n\n👤 {name}\n📱 {phone}\n📍 {address}"
)
ORDER_CONFIRM_COMMENT = "💬 {comment}"

ORDER_CANCELLED = "Buyurtma bekor qilindi."
ORDER_CART_VANISHED = "Savat bo'sh bo'lib qoldi. Qaytadan urinib ko'ring."
ORDER_ACCEPTED = (
    "✅ Buyurtma qabul qilindi!\n\n"
    "Raqami: <b>#{order_id}</b>\n"
    "Tez orada operator siz bilan bog'lanadi.\n\n"
    "To'lov usulini tanlang:"
)

NO_ORDERS = "Sizda hali buyurtma yo'q.\n🛍 Katalog dan boshlang."
MY_ORDERS_HEADER = "<b>Sizning buyurtmalaringiz</b>\n"
MY_ORDERS_LINE = (
    "🧾 <b>#{order_id}</b> — {total}\n   Holat: {status}\n   Sana: {created_at}\n"
)
ORDER_STATUS_CHANGED = "🔔 Buyurtma <b>#{order_id}</b> holati o'zgardi:\n{status}"

# ----------------------------------------------------------------- payment
PAY_CASH_DONE = (
    "✅ Buyurtma <b>#{order_id}</b> qabul qilindi.\n"
    "To'lov: yetkazib berilganda naqd.\n\nOperator tez orada qo'ng'iroq qiladi."
)
PAY_DISABLED = (
    "💳 Onlayn to'lov hozircha sozlanmagan (demo rejimi).\n\n"
    "Ishlab chiqarishda bu yerda Payme yoki Click to'lov oynasi ochiladi.\n"
    "Hozircha operator siz bilan bog'lanadi."
)
PAY_INVOICE_TITLE = "Buyurtma #{order_id}"
PAY_SUCCESS = (
    "✅ To'lov muvaffaqiyatli!\n\n"
    "Buyurtma <b>#{order_id}</b> to'landi.\nTez orada yetkazib beramiz. Rahmat! 🎉"
)
PAY_ALREADY_PAID = "Bu buyurtma allaqachon to'langan."
PAY_ORDER_NOT_FOUND = "Buyurtma topilmadi."
PAY_FAILED_PRECHECKOUT = "To'lovni amalga oshirib bo'lmadi. Qaytadan urinib ko'ring."

# ----------------------------------------------------------------- admin
ADMIN_PANEL = "Admin panel"
ADMIN_ONLY = "Bu bo'lim faqat adminlar uchun."

ADMIN_STATS = (
    "<b>📊 Statistika</b>\n\n"
    "👥 Foydalanuvchilar: <b>{users}</b>\n"
    "🟢 Faol (7 kun): <b>{active}</b>\n"
    "📦 Mahsulotlar: <b>{products}</b>\n"
    "🧾 Buyurtmalar: <b>{orders}</b>\n"
    "💳 To'langan: <b>{paid}</b>\n"
    "💰 Umumiy summa: <b>{revenue}</b>"
)

ADMIN_NO_ORDERS = "Hozircha buyurtma yo'q."
ADMIN_ORDER_HEADER = "🧾 <b>Buyurtma #{order_id}</b> — {status}\n"
ADMIN_ORDER_ITEM = "• {title} × {qty}"
ADMIN_ORDER_FOOTER = (
    "\n<b>Jami: {total}</b>\n👤 {name}\n📱 <code>{phone}</code>\n"
    "📍 {address}\n🕐 {created_at}"
)
ADMIN_NEW_ORDER_HEADER = "🆕 <b>Yangi buyurtma #{order_id}</b>\n"
ADMIN_PAID_NOTICE = "💳 Buyurtma #{order_id} <b>to'landi</b>."
ADMIN_STATUS_SET = "Holat: {status}"

ADMIN_ASK_CATEGORY_NAME = "Kategoriya nomini yozing ({language}):"
ADMIN_CATEGORY_ADDED = "✅ Kategoriya qo'shildi: <b>{title}</b>"
ADMIN_CATEGORY_EXISTS = "Bunday kategoriya allaqachon bor."
ADMIN_NEED_CATEGORY = "Avval kategoriya qo'shing (➕ Kategoriya)."
ADMIN_PICK_CATEGORY = "Qaysi kategoriyaga qo'shamiz?"
ADMIN_ASK_PRODUCT_TITLE = "Mahsulot nomini yozing ({language}):"
ADMIN_ASK_PRODUCT_DESC = "Tavsifini yozing ({language}). Kerak bo'lmasa <b>yo'q</b>:"
ADMIN_ASK_PRODUCT_PRICE = "Narxini yozing (faqat raqam, masalan 1150000):"
ADMIN_ASK_PRODUCT_PHOTO = "Mahsulot rasmini yuboring (rasm kerak bo'lmasa <b>yo'q</b>):"
ADMIN_NEED_PHOTO_OR_NO = "Rasm yuboring yoki <b>yo'q</b> deb yozing."
ADMIN_PRODUCT_ADDED = "✅ Mahsulot qo'shildi:\n<b>{title}</b> — {price}"

ADMIN_ASK_BROADCAST = "Yuboriladigan xabarni yozing (matn, rasm yoki video):"
ADMIN_BROADCAST_CONFIRM = (
    "Yuqoridagi xabar <b>{total}</b> foydalanuvchiga yuboriladi.\nDavom etamizmi?"
)
ADMIN_BROADCAST_CANCELLED = "Reklama bekor qilindi."
ADMIN_BROADCAST_STARTED = "📤 Yuborish boshlandi..."
ADMIN_BROADCAST_DONE = (
    "📊 <b>Reklama yakunlandi</b>\n\n"
    "✅ Yuborildi: <b>{sent}</b>\n"
    "❌ Yuborilmadi: <b>{failed}</b>\n"
    "⏱ Davomiyligi: <b>{seconds} s</b>"
)

ADMIN_ERROR_ALERT = (
    "🚨 <b>Xatolik</b>\n\n"
    "<b>Tur:</b> <code>{error_type}</code>\n"
    "<b>Handler:</b> <code>{where}</code>\n"
    "<b>Xabar:</b> <code>{message}</code>"
)

# ----------------------------------------------------------------- statuses
STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "✅ Qabul qilindi",
    "paid": "💳 To'landi",
    "shipping": "🚚 Yo'lda",
    "done": "🏁 Yakunlandi",
    "canceled": "❌ Bekor qilindi",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


# ----------------------------------------------------------------- buttons
BTN_CATALOG = "🛍 Katalog"
BTN_CART = "🛒 Savat"
BTN_MY_ORDERS = "📦 Buyurtmalarim"
BTN_CONTACTS = "ℹ️ Aloqa"
BTN_ADMIN = "⚙️ Admin panel"
BTN_CANCEL = "❌ Bekor qilish"
BTN_SEND_PHONE = "📱 Raqamni yuborish"
BTN_BACK_MAIN = "🔙 Asosiy menyu"
BTN_BACK_CATEGORIES = "🔙 Kategoriyalar"
BTN_BACK = "🔙 Orqaga"
BTN_ADD_TO_CART = "🛒 Savatga qo'shish"
BTN_CHECKOUT = "✅ Buyurtma berish"
BTN_CLEAR_CART = "🗑 Savatni tozalash"
BTN_CONFIRM = "✅ Tasdiqlash"
BTN_PAY_ONLINE = "💳 Onlayn to'lash"
BTN_PAY_CASH = "💵 Yetkazishda naqd"
BTN_ADD_PRODUCT = "➕ Mahsulot"
BTN_ADD_CATEGORY = "➕ Kategoriya"
BTN_ORDERS = "📋 Buyurtmalar"
BTN_STATS = "📊 Statistika"
BTN_BROADCAST = "📣 Reklama"
BTN_SEND = "📤 Yuborish"
BTN_LANGUAGE = "🌐 Til"

# Words that mean "skip this optional field".
CANCEL_WORDS = {"yo'q", "yoq", "yo`q", "нет", "не", "no", "-", "—"}

# Admin order-status button labels.
BTN_ST_ACCEPTED = "✅ Qabul qildim"
BTN_ST_SHIPPING = "🚚 Yo'lda"
BTN_ST_DONE = "🏁 Yakunlandi"
BTN_ST_CANCELED = "❌ Bekor"

# ----------------------------------------------------------------- currency
# Symbol per currency. UZS differs by language; ₽ and $ do not.
CURRENCY_SYMBOLS = {
    "UZS": "so'm",
    "RUB": "₽",
    "USD": "$",
}

CURRENCY_NAMES = {
    "UZS": "🇺🇿 So'm",
    "RUB": "🇷🇺 Rubl",
    "USD": "🇺🇸 Dollar",
}

BTN_CURRENCY = "💱 Valyuta"
CHOOSE_CURRENCY = "Valyutani tanlang:"
CURRENCY_SET = "✅ Valyuta o'zgartirildi: {currency}"
CURRENCY_RATE_NOTE = "Kurs: 1 {code} = {rate}"
CURRENCY_RATE_MISSING = (
    "⚠️ {code} kursi hozircha yo'q — narxlar so'mda ko'rsatilmoqda."
)
PAY_BASE_NOTICE = (
    "\n\n💳 To'lov so'mda amalga oshiriladi: <b>{amount}</b>\n"
    "<i>To'lov tizimlari (Payme, Click) faqat so'mni qabul qiladi.</i>"
)

# ----------------------------------------------------------------- admin rates
BTN_RATES = "💱 Kurslar"
ADMIN_RATES_HEADER = "<b>💱 Valyuta kurslari</b>\n\nBaza valyuta: <b>{base}</b>\n"
ADMIN_RATES_LINE = "{name}: 1 {code} = <b>{rate}</b> {base}\n<i>{source}, {updated}</i>"
ADMIN_RATES_NONE = "Hech qanday kurs yo'q. «Yangilash» ni bosing."
ADMIN_BTN_REFRESH_RATES = "🔄 CBU dan yangilash"
ADMIN_BTN_EDIT_RATE = "✏️ {code}"
ADMIN_RATES_REFRESH_OK = "✅ Kurslar yangilandi ({count} ta)."
ADMIN_RATES_REFRESH_FAIL = (
    "❌ CBU.uz javob bermadi. Eski kurslar saqlanib qoldi.\n"
    "Kursni qo'lda kiritishingiz mumkin."
)
ADMIN_ASK_RATE = (
    "1 {code} necha {base} turadi?\n"
    "Faqat raqam yozing (masalan 12101.84):"
)
ADMIN_RATE_SET = "✅ Kurs saqlandi: 1 {code} = {rate} {base}"
ADMIN_RATE_INVALID = "Kurs musbat son bo'lishi kerak. Qayta yozing:"
RATE_SOURCE_API = "CBU.uz"
RATE_SOURCE_MANUAL = "qo'lda"

# ----------------------------------------------------------------- admin price
ADMIN_ASK_PRICE_BASE = "Narxini {base} da yozing (faqat raqam, masalan 1150000):"
ADMIN_ASK_PRICE_CURRENCY = (
    "{name} dagi narxi.\n"
    "Aniq narx yozing yoki kurs bo'yicha hisoblansin desangiz "
    "«{auto}» tugmasini bosing.\n\n"
    "Taxminiy: <b>{suggested}</b>"
)
BTN_PRICE_AUTO = "🔄 Kurs bo'yicha"

# ----------------------------------------------------------------- stars
BTN_PAY_STARS = "⭐ Telegram Stars"
PAY_STARS_TITLE = "Buyurtma #{order_id}"
PAY_STARS_DEMO_NOTICE = (
    "⭐ <b>Demo to'lov</b>\n\n"
    "Buyurtma summasi: <b>{total}</b>\n"
    "Demo uchun undiriladi: <b>{stars} ⭐</b>\n\n"
    "<i>Bu portfolio namunasi. Haqiqiy do'konda to'liq summa undiriladi — "
    "PAYMENT_MODE=live qilinsa yetarli.</i>"
)
PAY_STARS_LIVE_NOTICE = (
    "⭐ To'lov Telegram Stars orqali: <b>{stars} ⭐</b>\n"
    "Buyurtma summasi: <b>{total}</b>"
)
PAY_STARS_UNAVAILABLE = "⭐ Stars orqali to'lov hozircha o'chirilgan."
PAY_STARS_RATE_MISSING = (
    "⭐ Hozircha Stars summasini hisoblab bo'lmadi (kurs yo'q).\n"
    "Operator siz bilan bog'lanadi."
)

# ----------------------------------------------------------------- providers
CHOOSE_PAYMENT = "To'lov usulini tanlang:"
PAY_GROUP_UZ = "🇺🇿 O'zbekiston"
PAY_GROUP_CIS = "🌍 MDH"

BTN_PAY_PAYME = "💙 Payme"
BTN_PAY_CLICK = "💚 Click"
BTN_PAY_CARD_UZ = "💳 Karta (Humo/Uzcard)"
BTN_PAY_SBP = "🇷🇺 СБП"
BTN_PAY_SBER = "🟢 Сбербанк karta"
BTN_PAY_YOOMONEY = "🟣 ЮMoney"

# --- manual transfer
PAY_MANUAL_INSTRUCTIONS = (
    "<b>{method}</b>\n\n"
    "To'lov summasi: <b>{amount}</b>\n"
    "Buyurtma: <b>#{order_id}</b>\n\n"
    "<b>Rekvizitlar:</b>\n"
    "{requisites}\n\n"
    "<b>Nima qilish kerak:</b>\n"
    "1. Yuqoridagi rekvizitlarga summani o'tkazing\n"
    "2. To'lov chekining <b>rasmini</b> shu yerga yuboring\n"
    "3. Admin tekshiradi va buyurtmani tasdiqlaydi\n\n"
    "Chek rasmini kutyapmiz 📷"
)
PAY_MANUAL_REQUISITE_CARD = "💳 <code>{value}</code>"
PAY_MANUAL_REQUISITE_PHONE = "📱 <code>{value}</code>"
PAY_MANUAL_REQUISITE_HOLDER = "👤 {value}"
PAY_MANUAL_REQUISITE_BANK = "🏦 {value}"

PAY_RECEIPT_NEED_PHOTO = "Iltimos, chekning <b>rasmini</b> yuboring (matn emas)."
PAY_RECEIPT_RECEIVED = (
    "✅ Chek qabul qilindi.\n\n"
    "Buyurtma <b>#{order_id}</b> tekshiruvga yuborildi. "
    "Admin tasdiqlagach xabar beramiz."
)
PAY_RECEIPT_APPROVED = (
    "✅ To'lov tasdiqlandi!\n\n"
    "Buyurtma <b>#{order_id}</b> to'landi. Tez orada yetkazib beramiz. Rahmat! 🎉"
)
PAY_RECEIPT_REJECTED = (
    "❌ Chek tasdiqlanmadi.\n\n"
    "Buyurtma <b>#{order_id}</b> bo'yicha to'lov topilmadi. "
    "Iltimos, operator bilan bog'laning yoki chekni qayta yuboring."
)

# --- telegram-payments providers without a token
PAY_DEMO_WALKTHROUGH = (
    "<b>{method}</b>\n\n"
    "To'lov summasi: <b>{amount}</b>\n"
    "Buyurtma: <b>#{order_id}</b>\n\n"
    "<b>Jonli rejimda qanday ishlaydi:</b>\n"
    "1. Bu tugma bosilganda {method} to'lov oynasi ochiladi\n"
    "2. Mijoz kartasini tanlaydi va SMS kodni tasdiqlaydi\n"
    "3. To'lov o'tgach bot buyurtmani avtomatik «to'landi» deb belgilaydi\n"
    "4. Admin guruhga darhol xabar tushadi\n\n"
    "<i>Demo: {method} merchant kaliti ulanmagan. Kalit .env ga qo'yilsa "
    "shu tugma haqiqiy to'lov oynasini ochadi — kodni o'zgartirish shart emas.</i>"
)
BTN_PAY_BY_RECEIPT = "💳 Karta orqali to'lash"
BTN_PAY_BACK = "🔙 Boshqa usul"

# --- admin review
ADMIN_RECEIPT_HEADER = (
    "🧾 <b>To'lov cheki — buyurtma #{order_id}</b>\n\n"
    "Usul: <b>{method}</b>\n"
    "Summa: <b>{amount}</b>\n"
    "👤 {name}\n"
    "📱 <code>{phone}</code>"
)
BTN_RECEIPT_APPROVE = "✅ To'lovni tasdiqlash"
BTN_RECEIPT_REJECT = "❌ To'lovni rad etish"
ADMIN_RECEIPT_APPROVED = "✅ Buyurtma #{order_id} to'langan deb belgilandi."
ADMIN_RECEIPT_REJECTED = "❌ Buyurtma #{order_id} cheki rad etildi."
ADMIN_RECEIPT_ALREADY = "Bu chek allaqachon ko'rib chiqilgan."

# ----------------------------------------------------------------- profile
ORDER_PROFILE_SAVED = (
    "<b>Buyurtma rasmiylashtirish</b>\n\n"
    "Saqlangan ma'lumotlaringiz:\n"
    "👤 {name}\n"
    "📱 {phone}\n\n"
    "Manzilni yozing (shahar, ko'cha, uy, xonadon):"
)
BTN_EDIT_PROFILE = "✏️ Ism/telefonni o'zgartirish"
PROFILE_CLEARED = "Ma'lumotlar tozalandi. Qaytadan kiritamiz."
PAY_RECEIPT_NEED_IMAGE = (
    "Iltimos, chekni <b>rasm</b> yoki <b>rasm fayli</b> ko'rinishida yuboring.\n"
    "PDF va matn qabul qilinmaydi."
)

# ----------------------------------------------------------------- demo safety
PAY_MANUAL_DEMO_WARNING = (
    "\n\n⚠️ <b>DIQQAT: bu demo bot.</b>\n"
    "Rekvizitlar haqiqiy emas — <b>pul o'tkazmang</b>.\n"
    "Oqimni ko'rish uchun istalgan rasmni chek sifatida yuboring."
)

# ----------------------------------------------------------------- limits
ORDER_TOO_MANY_OPEN = (
    "⚠️ Sizda {count} ta yakunlanmagan buyurtma bor.\n\n"
    "Avval ularni to'lang yoki operator yakunlashini kuting, "
    "keyin yangi buyurtma bering."
)
