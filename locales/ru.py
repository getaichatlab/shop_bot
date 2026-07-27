"""Russian locale.

Mirrors locales/uz.py key for key. Missing keys are caught by
tests/test_locales.py, which asserts both files expose exactly the same names.
"""
from __future__ import annotations

LANG_CODE = "ru"
LANG_NAME = "🇷🇺 Русский"


# ----------------------------------------------------------------- common
WELCOME = (
    "Здравствуйте, <b>{name}</b>! 👋\n\n"
    "Это бот интернет-магазина.\n"
    "Выберите товар в каталоге, добавьте в корзину и оформите заказ.\n\n"
    "Начните с меню ниже 👇"
)

HELP = (
    "<b>Как пользоваться ботом</b>\n\n"
    "🛍 <b>Каталог</b> — просмотр товаров и добавление в корзину\n"
    "🛒 <b>Корзина</b> — изменение количества, оформление заказа\n"
    "📦 <b>Мои заказы</b> — отслеживание статуса заказа\n"
    "ℹ️ <b>Контакты</b> — связь с оператором\n\n"
    "Сменить язык: /language\n"
    "Чтобы отменить действие, напишите /cancel на любом шаге."
)

# ----------------------------------------------------------------- language
CHOOSE_LANGUAGE = "Выберите язык:"
LANGUAGE_SET = "✅ Язык изменён: Русский"

CONTACTS = (
    "<b>Свяжитесь с нами</b>\n\n"
    "📞 Телефон: +998 90 000 00 00\n"
    "🕐 Время работы: 09:00 – 20:00, понедельник–суббота\n"
    "📍 Адрес: город Ташкент\n\n"
    "Если у вас есть вопрос — напишите сюда, оператор ответит."
)

MAIN_MENU = "Главное меню"
CANCELLED = "Отменено."
NOTHING_TO_CANCEL = "Сейчас нечего отменять."
LOADING = "⏳ Секунду..."
GENERIC_ERROR = (
    "⚠️ Произошла непредвиденная ошибка. Мы уже знаем о ней.\n"
    "Пожалуйста, попробуйте чуть позже или нажмите /start."
)
THROTTLED = "⏳ Слишком быстро. Подождите секунду."

# ----------------------------------------------------------------- catalog
CHOOSE_CATEGORY = "Выберите категорию:"
CHOOSE_PRODUCT = "Выберите товар:"
CATALOG_EMPTY = "Каталог пока пуст. Товары появятся в ближайшее время."
CATEGORY_EMPTY = "В этой категории нет товаров."
PRODUCT_NOT_FOUND = "Товар не найден или снят с продажи."
NO_DESCRIPTION = "Описание не указано."

PRODUCT_CARD = (
    "<b>{title}</b>\n\n"
    "{description}\n\n"
    "💰 Цена: <b>{price}</b>"
)

ADDED_TO_CART = "Добавлено в корзину ✅\nИтого: {total}"

# ----------------------------------------------------------------- cart
CART_EMPTY = "Ваша корзина пуста 🕸\n\n🛍 Выберите товар в каталоге."
CART_HEADER = "<b>🛒 Ваша корзина</b>\n"
CART_LINE = "• {title}\n   {qty} × {price} = <b>{subtotal}</b>"
CART_TOTAL = "\n<b>Итого: {total}</b>"
CART_CLEARED = "Корзина очищена 🗑"
ITEM_REMOVED = "Удалено"

# ----------------------------------------------------------------- order
ORDER_STEP_NAME = "<b>Оформление заказа — 1/4</b>\n\nНапишите ваше имя и фамилию:"
ORDER_STEP_PHONE = (
    "<b>2/4</b>\n\nОтправьте ваш номер телефона.\n"
    "Нажмите кнопку ниже или введите вручную (например +998901234567):"
)
ORDER_STEP_ADDRESS = (
    "<b>3/4</b>\n\nНапишите адрес доставки\n(город, улица, дом, квартира):"
)
ORDER_STEP_COMMENT = (
    "<b>4/4</b>\n\nОставите комментарий? (время доставки, особые пожелания)\n"
    "Если не нужно — напишите <b>нет</b>:"
)

ERR_NAME_SHORT = "Имя слишком короткое. Напишите имя и фамилию полностью:"
ERR_NAME_LONG = "Имя слишком длинное (максимум {limit} символов). Напишите короче:"
ERR_PHONE_INVALID = (
    "Неверный номер. Пример: <code>+998901234567</code>\nОтправьте ещё раз:"
)
ERR_ADDRESS_SHORT = "Адрес слишком короткий. Укажите точнее:"
ERR_ADDRESS_LONG = "Адрес слишком длинный (максимум {limit} символов). Напишите короче:"
ERR_COMMENT_LONG = "Комментарий слишком длинный (максимум {limit} символов). Напишите короче:"
ERR_TEXT_EXPECTED = "Пожалуйста, отправьте текстом."
ERR_PRICE_INVALID = "Цена должна состоять только из цифр. Напишите ещё раз:"

ORDER_CHECK = "Проверьте 👇"
ORDER_CONFIRM_HEADER = "<b>Подтвердите заказ</b>\n"
ORDER_CONFIRM_LINE = "• {title} × {qty} = {subtotal}"
ORDER_CONFIRM_FOOTER = (
    "\n<b>Итого: {total}</b>\n\n👤 {name}\n📱 {phone}\n📍 {address}"
)
ORDER_CONFIRM_COMMENT = "💬 {comment}"

ORDER_CANCELLED = "Заказ отменён."
ORDER_CART_VANISHED = "Корзина оказалась пустой. Попробуйте ещё раз."
ORDER_ACCEPTED = (
    "✅ Заказ принят!\n\n"
    "Номер: <b>#{order_id}</b>\n"
    "Оператор свяжется с вами в ближайшее время.\n\n"
    "Выберите способ оплаты:"
)

NO_ORDERS = "У вас пока нет заказов.\n🛍 Начните с каталога."
MY_ORDERS_HEADER = "<b>Ваши заказы</b>\n"
MY_ORDERS_LINE = (
    "🧾 <b>#{order_id}</b> — {total}\n   Статус: {status}\n   Дата: {created_at}\n"
)
ORDER_STATUS_CHANGED = "🔔 Статус заказа <b>#{order_id}</b> изменился:\n{status}"

# ----------------------------------------------------------------- payment
PAY_CASH_DONE = (
    "✅ Заказ <b>#{order_id}</b> принят.\n"
    "Оплата: наличными при доставке.\n\nОператор скоро позвонит."
)
PAY_DISABLED = (
    "💳 Онлайн-оплата пока не настроена (демо-режим).\n\n"
    "В рабочей версии здесь открывается окно оплаты Payme или Click.\n"
    "Сейчас с вами свяжется оператор."
)
PAY_INVOICE_TITLE = "Заказ #{order_id}"
PAY_SUCCESS = (
    "✅ Оплата прошла успешно!\n\n"
    "Заказ <b>#{order_id}</b> оплачен.\nСкоро доставим. Спасибо! 🎉"
)
PAY_ALREADY_PAID = "Этот заказ уже оплачен."
PAY_ORDER_NOT_FOUND = "Заказ не найден."
PAY_FAILED_PRECHECKOUT = "Не удалось провести оплату. Попробуйте ещё раз."

# ----------------------------------------------------------------- admin
ADMIN_PANEL = "Админ-панель"
ADMIN_ONLY = "Этот раздел только для администраторов."

ADMIN_STATS = (
    "<b>📊 Статистика</b>\n\n"
    "👥 Пользователей: <b>{users}</b>\n"
    "🟢 Активных (7 дней): <b>{active}</b>\n"
    "📦 Товаров: <b>{products}</b>\n"
    "🧾 Заказов: <b>{orders}</b>\n"
    "💳 Оплачено: <b>{paid}</b>\n"
    "💰 Общая сумма: <b>{revenue}</b>"
)

ADMIN_NO_ORDERS = "Заказов пока нет."
ADMIN_ORDER_HEADER = "🧾 <b>Заказ #{order_id}</b> — {status}\n"
ADMIN_ORDER_ITEM = "• {title} × {qty}"
ADMIN_ORDER_FOOTER = (
    "\n<b>Итого: {total}</b>\n👤 {name}\n📱 <code>{phone}</code>\n"
    "📍 {address}\n🕐 {created_at}"
)
ADMIN_NEW_ORDER_HEADER = "🆕 <b>Новый заказ #{order_id}</b>\n"
ADMIN_PAID_NOTICE = "💳 Заказ #{order_id} <b>оплачен</b>."
ADMIN_STATUS_SET = "Статус: {status}"

ADMIN_ASK_CATEGORY_NAME = "Напишите название категории ({language}):"
ADMIN_CATEGORY_ADDED = "✅ Категория добавлена: <b>{title}</b>"
ADMIN_CATEGORY_EXISTS = "Такая категория уже существует."
ADMIN_NEED_CATEGORY = "Сначала добавьте категорию (➕ Категория)."
ADMIN_PICK_CATEGORY = "В какую категорию добавляем?"
ADMIN_ASK_PRODUCT_TITLE = "Напишите название товара ({language}):"
ADMIN_ASK_PRODUCT_DESC = "Напишите описание ({language}). Если не нужно — <b>нет</b>:"
ADMIN_ASK_PRODUCT_PRICE = "Напишите цену (только цифры, например 1150000):"
ADMIN_ASK_PRODUCT_PHOTO = "Отправьте фото товара (если фото не нужно — <b>нет</b>):"
ADMIN_NEED_PHOTO_OR_NO = "Отправьте фото или напишите <b>нет</b>."
ADMIN_PRODUCT_ADDED = "✅ Товар добавлен:\n<b>{title}</b> — {price}"

ADMIN_ASK_BROADCAST = "Напишите сообщение для рассылки (текст, фото или видео):"
ADMIN_BROADCAST_CONFIRM = (
    "Сообщение выше будет отправлено <b>{total}</b> пользователям.\nПродолжаем?"
)
ADMIN_BROADCAST_CANCELLED = "Рассылка отменена."
ADMIN_BROADCAST_STARTED = "📤 Отправка началась..."
ADMIN_BROADCAST_DONE = (
    "📊 <b>Рассылка завершена</b>\n\n"
    "✅ Отправлено: <b>{sent}</b>\n"
    "❌ Не отправлено: <b>{failed}</b>\n"
    "⏱ Длительность: <b>{seconds} с</b>"
)

ADMIN_ERROR_ALERT = (
    "🚨 <b>Ошибка</b>\n\n"
    "<b>Тип:</b> <code>{error_type}</code>\n"
    "<b>Handler:</b> <code>{where}</code>\n"
    "<b>Сообщение:</b> <code>{message}</code>"
)

# ----------------------------------------------------------------- statuses
STATUS_LABELS = {
    "new": "🆕 Новый",
    "accepted": "✅ Принят",
    "paid": "💳 Оплачен",
    "shipping": "🚚 В пути",
    "done": "🏁 Завершён",
    "canceled": "❌ Отменён",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


# ----------------------------------------------------------------- buttons
BTN_CATALOG = "🛍 Каталог"
BTN_CART = "🛒 Корзина"
BTN_MY_ORDERS = "📦 Мои заказы"
BTN_CONTACTS = "ℹ️ Контакты"
BTN_ADMIN = "⚙️ Админ-панель"
BTN_CANCEL = "❌ Отменить"
BTN_SEND_PHONE = "📱 Отправить номер"
BTN_BACK_MAIN = "🔙 Главное меню"
BTN_BACK_CATEGORIES = "🔙 Категории"
BTN_BACK = "🔙 Назад"
BTN_ADD_TO_CART = "🛒 В корзину"
BTN_CHECKOUT = "✅ Оформить заказ"
BTN_CLEAR_CART = "🗑 Очистить корзину"
BTN_CONFIRM = "✅ Подтвердить"
BTN_PAY_ONLINE = "💳 Оплатить онлайн"
BTN_PAY_CASH = "💵 Наличными при доставке"
BTN_ADD_PRODUCT = "➕ Товар"
BTN_ADD_CATEGORY = "➕ Категория"
BTN_ORDERS = "📋 Заказы"
BTN_STATS = "📊 Статистика"
BTN_BROADCAST = "📣 Рассылка"
BTN_SEND = "📤 Отправить"
BTN_LANGUAGE = "🌐 Язык"

# Words that mean "skip this optional field".
CANCEL_WORDS = {"нет", "не", "-", "—", "yo'q", "yoq", "no"}

# Admin order-status button labels.
BTN_ST_ACCEPTED = "✅ Принял"
BTN_ST_SHIPPING = "🚚 В пути"
BTN_ST_DONE = "🏁 Завершён"
BTN_ST_CANCELED = "❌ Отмена"

# ----------------------------------------------------------------- currency
# Symbol per currency. UZS differs by language; ₽ and $ do not.
CURRENCY_SYMBOLS = {
    "UZS": "сум",
    "RUB": "₽",
    "USD": "$",
}

CURRENCY_NAMES = {
    "UZS": "🇺🇿 Сум",
    "RUB": "🇷🇺 Рубль",
    "USD": "🇺🇸 Доллар",
}

BTN_CURRENCY = "💱 Валюта"
CHOOSE_CURRENCY = "Выберите валюту:"
CURRENCY_SET = "✅ Валюта изменена: {currency}"
CURRENCY_RATE_NOTE = "Курс: 1 {code} = {rate}"
CURRENCY_RATE_MISSING = (
    "⚠️ Курс {code} пока недоступен — цены показаны в сумах."
)
PAY_BASE_NOTICE = (
    "\n\n💳 Оплата проходит в сумах: <b>{amount}</b>\n"
    "<i>Платёжные системы (Payme, Click) принимают только сум.</i>"
)

# ----------------------------------------------------------------- admin rates
BTN_RATES = "💱 Курсы"
ADMIN_RATES_HEADER = "<b>💱 Курсы валют</b>\n\nБазовая валюта: <b>{base}</b>\n"
ADMIN_RATES_LINE = "{name}: 1 {code} = <b>{rate}</b> {base}\n<i>{source}, {updated}</i>"
ADMIN_RATES_NONE = "Курсов пока нет. Нажмите «Обновить»."
ADMIN_BTN_REFRESH_RATES = "🔄 Обновить с ЦБ"
ADMIN_BTN_EDIT_RATE = "✏️ {code}"
ADMIN_RATES_REFRESH_OK = "✅ Курсы обновлены ({count})."
ADMIN_RATES_REFRESH_FAIL = (
    "❌ CBU.uz не отвечает. Прежние курсы сохранены.\n"
    "Курс можно ввести вручную."
)
ADMIN_ASK_RATE = (
    "Сколько {base} стоит 1 {code}?\n"
    "Напишите только число (например 12101.84):"
)
ADMIN_RATE_SET = "✅ Курс сохранён: 1 {code} = {rate} {base}"
ADMIN_RATE_INVALID = "Курс должен быть положительным числом. Напишите ещё раз:"
RATE_SOURCE_API = "ЦБ РУз"
RATE_SOURCE_MANUAL = "вручную"

# ----------------------------------------------------------------- admin price
ADMIN_ASK_PRICE_BASE = "Напишите цену в {base} (только цифры, например 1150000):"
ADMIN_ASK_PRICE_CURRENCY = (
    "Цена в {name}.\n"
    "Напишите точную цену или нажмите «{auto}», "
    "чтобы посчитать по курсу.\n\n"
    "Ориентировочно: <b>{suggested}</b>"
)
BTN_PRICE_AUTO = "🔄 По курсу"

# ----------------------------------------------------------------- stars
BTN_PAY_STARS = "⭐ Telegram Stars"
PAY_STARS_TITLE = "Заказ #{order_id}"
PAY_STARS_DEMO_NOTICE = (
    "⭐ <b>Демо-оплата</b>\n\n"
    "Сумма заказа: <b>{total}</b>\n"
    "Спишется для демонстрации: <b>{stars} ⭐</b>\n\n"
    "<i>Это портфолио-демо. В рабочем магазине списывается полная сумма — "
    "достаточно поставить PAYMENT_MODE=live.</i>"
)
PAY_STARS_LIVE_NOTICE = (
    "⭐ Оплата через Telegram Stars: <b>{stars} ⭐</b>\n"
    "Сумма заказа: <b>{total}</b>"
)
PAY_STARS_UNAVAILABLE = "⭐ Оплата через Stars сейчас отключена."
PAY_STARS_RATE_MISSING = (
    "⭐ Пока не удалось рассчитать сумму в Stars (нет курса).\n"
    "С вами свяжется оператор."
)

# ----------------------------------------------------------------- providers
CHOOSE_PAYMENT = "Выберите способ оплаты:"
PAY_GROUP_UZ = "🇺🇿 Узбекистан"
PAY_GROUP_CIS = "🌍 СНГ"

BTN_PAY_PAYME = "💙 Payme"
BTN_PAY_CLICK = "💚 Click"
BTN_PAY_CARD_UZ = "💳 Карта (Humo/Uzcard)"
BTN_PAY_SBP = "🇷🇺 СБП"
BTN_PAY_SBER = "🟢 Карта Сбербанка"
BTN_PAY_YOOMONEY = "🟣 ЮMoney"

# --- manual transfer
PAY_MANUAL_INSTRUCTIONS = (
    "<b>{method}</b>\n\n"
    "Сумма к оплате: <b>{amount}</b>\n"
    "Заказ: <b>#{order_id}</b>\n\n"
    "<b>Реквизиты:</b>\n"
    "{requisites}\n\n"
    "<b>Что сделать:</b>\n"
    "1. Переведите сумму по реквизитам выше\n"
    "2. Отправьте сюда <b>фото</b> чека\n"
    "3. Администратор проверит и подтвердит заказ\n\n"
    "Ждём фото чека 📷"
)
PAY_MANUAL_REQUISITE_CARD = "💳 <code>{value}</code>"
PAY_MANUAL_REQUISITE_PHONE = "📱 <code>{value}</code>"
PAY_MANUAL_REQUISITE_HOLDER = "👤 {value}"
PAY_MANUAL_REQUISITE_BANK = "🏦 {value}"

PAY_RECEIPT_NEED_PHOTO = "Пожалуйста, пришлите <b>фото</b> чека (не текст)."
PAY_RECEIPT_RECEIVED = (
    "✅ Чек получен.\n\n"
    "Заказ <b>#{order_id}</b> отправлен на проверку. "
    "Сообщим, как только администратор подтвердит."
)
PAY_RECEIPT_APPROVED = (
    "✅ Оплата подтверждена!\n\n"
    "Заказ <b>#{order_id}</b> оплачен. Скоро доставим. Спасибо! 🎉"
)
PAY_RECEIPT_REJECTED = (
    "❌ Чек не подтверждён.\n\n"
    "Оплата по заказу <b>#{order_id}</b> не найдена. "
    "Свяжитесь с оператором или отправьте чек ещё раз."
)

# --- telegram-payments providers without a token
PAY_DEMO_WALKTHROUGH = (
    "<b>{method}</b>\n\n"
    "Сумма к оплате: <b>{amount}</b>\n"
    "Заказ: <b>#{order_id}</b>\n\n"
    "<b>Как это работает в рабочем режиме:</b>\n"
    "1. По нажатию открывается платёжное окно {method}\n"
    "2. Клиент выбирает карту и подтверждает код из SMS\n"
    "3. После оплаты бот сам помечает заказ «оплачен»\n"
    "4. В админ-чат сразу приходит уведомление\n\n"
    "<i>Демо: мерчант-ключ {method} не подключён. Достаточно положить ключ "
    "в .env — эта же кнопка откроет настоящее окно оплаты, код менять не нужно.</i>"
)
BTN_PAY_BY_RECEIPT = "💳 Оплатить картой"
BTN_PAY_BACK = "🔙 Другой способ"

# --- admin review
ADMIN_RECEIPT_HEADER = (
    "🧾 <b>Чек об оплате — заказ #{order_id}</b>\n\n"
    "Способ: <b>{method}</b>\n"
    "Сумма: <b>{amount}</b>\n"
    "👤 {name}\n"
    "📱 <code>{phone}</code>"
)
BTN_RECEIPT_APPROVE = "✅ Подтвердить оплату"
BTN_RECEIPT_REJECT = "❌ Отклонить оплату"
ADMIN_RECEIPT_APPROVED = "✅ Заказ #{order_id} отмечен оплаченным."
ADMIN_RECEIPT_REJECTED = "❌ Чек по заказу #{order_id} отклонён."
ADMIN_RECEIPT_ALREADY = "Этот чек уже рассмотрен."

# ----------------------------------------------------------------- profile
ORDER_PROFILE_SAVED = (
    "<b>Оформление заказа</b>\n\n"
    "Ваши сохранённые данные:\n"
    "👤 {name}\n"
    "📱 {phone}\n\n"
    "Напишите адрес доставки (город, улица, дом, квартира):"
)
BTN_EDIT_PROFILE = "✏️ Изменить имя/телефон"
PROFILE_CLEARED = "Данные очищены. Введём заново."
PAY_RECEIPT_NEED_IMAGE = (
    "Пожалуйста, пришлите чек <b>фото</b> или <b>файлом-изображением</b>.\n"
    "PDF и текст не принимаются."
)

# ----------------------------------------------------------------- demo safety
PAY_MANUAL_DEMO_WARNING = (
    "\n\n⚠️ <b>ВНИМАНИЕ: это демо-бот.</b>\n"
    "Реквизиты ненастоящие — <b>не переводите деньги</b>.\n"
    "Чтобы увидеть процесс, пришлите любое изображение вместо чека."
)

# ----------------------------------------------------------------- limits
ORDER_TOO_MANY_OPEN = (
    "⚠️ У вас {count} незавершённых заказов.\n\n"
    "Сначала оплатите их или дождитесь, пока оператор их закроет, "
    "затем оформляйте новый."
)
