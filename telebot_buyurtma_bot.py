import os
import threading
import uuid
import telebot
from aiohttp import web
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_CHAT_ID = "7818782335"

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN qatoriga BotFather bergan haqiqiy tokenni kiriting.")
if not OWNER_CHAT_ID.isdigit():
    raise RuntimeError("OWNER_CHAT_ID qatoriga raqamli chat ID ni kiriting.")

OWNER_CHAT_ID = int(OWNER_CHAT_ID)
PORT = int(os.getenv("PORT", "10000"))
bot = telebot.TeleBot(BOT_TOKEN)

MAIN_MENU = {
    "💻 Kompyuter xizmatlari": "Kompyuter xizmatlari",
    "📱 Telefon xizmatlari": "Telefon xizmatlari",
    "🖼 Rasm chiqarish": "Rasm chiqarish",
    "💌 Taklifnoma chiqarish": "Taklifnoma tayyorlash va chiqarish",
    "🥂 Bokalga rasm tushirish": "Bokalga rasm tushirish",
    "👕 Futbolkaga rasm tushirish": "Futbolkaga rasm tushirish",
    "🖨 Pechat/Kserokopiya": "Pechat / kserokopiya",
    "🐍 Python xizmatlari": "Python xizmatlari",
}

SUBSERVICES = {
    "💻 Kompyuter xizmatlari": [
        "Windows o'rnatish va aktivatsiya qilish",
        "Dasturlar o'rnatish",
        "Kompyuter sozlamalarini to'g'rilash",
        "Viruslarni tozalash",
        "Word va Excel xizmatlari",
        "Photoshop xizmatlari",
        "PowerPoint slayd tayyorlash",
        "Ariza yozish va yuborish",
        "DTM / OTM hujjatlarini topshirish",
    ],
    "📱 Telefon xizmatlari": [
        "Telefon proshivka qilish",
        "Ekran kodini ochish",
        "Sozlamalarni to'g'rilash",
        "Dastur o'rnatish va ishlashini to'g'rilash",
    ],
    "🖼 Rasm chiqarish": [
        "3x4 hujjat uchun rasm",
        "10x15 oilaviy rasm",
        "Ramkaga solinadigan katta rasm",
        "Fotoalbom rasmlari",
    ],
    "🐍 Python xizmatlari": [
        "Telegram bot yasab berish",
        "Sayt yasab berish",
        "Kichik ilovalar yasab berish",
    ],
    "🖨 Pechat/Kserokopiya": [
        "PDF/fayllarni qog'ozga chiqarish",
        "Oq-qora hujjat chiqarish",
        "Rangli hujjat chiqarish",
        "Kserokopiya qilish",
        "Skaner qilish va nusxa ko'chirish",
        "Taklifnoma chiqarish",
    ],
}

# Ma'lumotlar bot ishlayotgan vaqt davomida xotirada turadi.
user_orders = {}
submitted_orders = {}

MAIN_BUTTONS = list(MAIN_MENU.keys()) + ["💰 Narxlar", "📞 Bog'lanish"]
BACK_BUTTON = "⬅️ Bosh menyu"
SEND_BUTTON = "✅ Buyurtmani yuborish"
ADD_MEDIA_BUTTON = "📷 Rasm/fayl qo'shish"
ADD_NOTE_BUTTON = "✍️ Izoh yozish"
SKIP_BUTTON = "⏭ Davom etish"
PHONE_BUTTON = "📞 Telefon raqam qoldirish"


def make_keyboard(rows, include_back=True):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in rows:
        keyboard.row(*[types.KeyboardButton(label) for label in row])
    if include_back:
        keyboard.row(BACK_BUTTON)
    return keyboard


def main_keyboard():
    rows = [MAIN_BUTTONS[i:i + 2] for i in range(0, len(MAIN_BUTTONS), 2)]
    return make_keyboard(rows, include_back=False)


def submenu_keyboard(options):
    rows = [[option] for option in options]
    return make_keyboard(rows)


def media_keyboard():
    return make_keyboard([[ADD_NOTE_BUTTON, PHONE_BUTTON], [SKIP_BUTTON]])


def phone_keyboard():
    return make_keyboard([[SKIP_BUTTON]])

def confirm_keyboard():
    return make_keyboard([[SEND_BUTTON], [ADD_MEDIA_BUTTON, ADD_NOTE_BUTTON], [PHONE_BUTTON]])


def begin_order(message, main_button):
    user_id = message.from_user.id
    service_name = MAIN_MENU[main_button]
    user_orders[user_id] = {
        "service": service_name,
        "detail": "",
        "photos": [],
        "files": [],
        "note": "",
        "phone": "",
        "step": "media",
    }
    bot.send_message(
        message.chat.id,
        f"Tanlandi: {service_name}\n\n"
        "Buyurtma qanday bo'lishini ko'rsatadigan rasm yoki fayl yuboring. "
        "Bir nechta rasm yuborishingiz mumkin. Keyin izoh yozing.\n\n"
        "Rasm bo'lmasa, “Davom etish”ni bosing. Buyurtmani oxirida "
        "“Buyurtmani yuborish” tugmasi bilan jo'natasiz.",
        reply_markup=media_keyboard(),
    )


def show_confirmation(chat_id, user_id):
    order = user_orders[user_id]
    order["step"] = "confirm"
    media_count = len(order["photos"]) + len(order["files"])
    note = order["note"] or "Izoh yozilmagan"
    bot.send_message(
        chat_id,
        "Buyurtma ma'lumotlari:\n"
        f"Xizmat: {order['service']}\n"
        f"Turi: {order['detail'] or 'Ko\u2018rsatilmagan'}\n"
        f"Rasm/fayl: {media_count} ta\n"
        f"Telefon: {order.get('phone') or 'kiritilmagan'}\n"
        f"Izoh: {note}\n\n"
        "Hammasi to'g'ri bo'lsa, “Buyurtmani yuborish”ni bosing.",
        reply_markup=confirm_keyboard(),
    )


def submit_order(message):
    user_id = message.from_user.id
    order = user_orders.get(user_id)
    if not order:
        bot.send_message(message.chat.id, "Avval menyudan xizmatni tanlang.", reply_markup=main_keyboard())
        return

    order_id = uuid.uuid4().hex[:8]
    order["user_id"] = user_id
    order["customer_name"] = message.from_user.full_name
    order["username"] = message.from_user.username or "username yo'q"
    order["status"] = "new"
    submitted_orders[order_id] = order.copy()

    admin_text = (
        f"📩 YANGI BUYURTMA #{order_id}\n"
        f"Xizmat: {order['service']}\n"
        f"Turi: {order['detail'] or 'Ko\u2018rsatilmagan'}\n"
        f"Mijoz: {order['customer_name']} (@{order['username']})\n"
        f"Mijoz chat ID: {user_id}\n"
        f"Telefon: {order.get('phone') or 'kiritilmagan'}\n"
        f"Izoh: {order['note'] or 'yo\u2018q'}"
    )
    admin_keyboard = types.InlineKeyboardMarkup()
    admin_keyboard.row(
        types.InlineKeyboardButton("⏳ 2-3 soatda tayyor", callback_data=f"ord|{order_id}|eta2"),
        types.InlineKeyboardButton("⏳ 4-5 soatda tayyor", callback_data=f"ord|{order_id}|eta2"),
        types.InlineKeyboardButton("⏳ 6-7 soatda tayyor", callback_data=f"ord|{order_id}|eta2"),
        types.InlineKeyboardButton("⏳ 8-9 soatda tayyor", callback_data=f"ord|{order_id}|eta2"),
        types.InlineKeyboardButton("📅 Ertaga tayyor", callback_data=f"ord|{order_id}|tomorrow"),
        types.InlineKeyboardButton("📅 2-3 kunda tayyor", callback_data=f"ord|{order_id}|tomorrow"),
        types.InlineKeyboardButton("📅 4-5 kunda tayyor", callback_data=f"ord|{order_id}|tomorrow"),
    )
    admin_keyboard.row(
        types.InlineKeyboardButton("✅ Buyurtma tayyor", callback_data=f"ord|{order_id}|ready")
    )
    try:
        bot.send_message(OWNER_CHAT_ID, admin_text, reply_markup=admin_keyboard)
    except Exception as error:
        print(f"Admin chatga buyurtma yuborilmadi: {error}")
        bot.send_message(
            message.chat.id,
            "Buyurtmani adminga yuborishda xatolik yuz berdi. Iltimos, telefon orqali bog'laning: +998 88 311 27 01",
            reply_markup=main_keyboard(),
        )
        return

    for photo_id in order["photos"]:
        bot.send_photo(OWNER_CHAT_ID, photo_id)
    for file_id, file_name in order["files"]:
        bot.send_document(OWNER_CHAT_ID, file_id, caption=file_name or "Mijoz yuborgan fayl")

    # Admin chatida pastki menyuni chiqarish.
    bot.send_message(
        OWNER_CHAT_ID,
        "Admin menyusi: yuqoridagi tugmalar orqali buyurtma holatini belgilang.",
        reply_markup=main_keyboard(),
    )
    user_orders.pop(user_id, None)
    bot.send_message(
        message.chat.id,
        f"✅ Buyurtmangiz yuborildi! Buyurtma raqami: #{order_id}.\n"
        "Tayyor bo'lganda bot sizga xabar beradi.",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["start"])
def start(message):
    user_orders.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! 👋\n\n"
        "UMIRZOQ KOMPYUTER XIZMATLARIGA xush kelibsiz.\n\n"
        "Kerakli xizmatni tanlang:",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["cancel"])
def cancel(message):
    user_orders.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Buyurtma bekor qilindi.", reply_markup=main_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith("ord|"))
def admin_order_action(call):
    if call.from_user.id != OWNER_CHAT_ID:
        bot.answer_callback_query(call.id, "Bu tugma faqat xizmat egasi uchun.", show_alert=True)
        return

    try:
        _, order_id, action = call.data.split("|")
        order = submitted_orders[order_id]
    except (ValueError, KeyError):
        bot.answer_callback_query(call.id, "Buyurtma topilmadi.", show_alert=True)
        return

    customer_id = order["user_id"]
    if action == "eta2":
        bot.send_message(customer_id, f"⏳ Buyurtmangiz #{order_id} taxminan 2-3 soatda tayyor bo'ladi.")
        bot.answer_callback_query(call.id, "Mijozga 2-3 soat xabari yuborildi.")
    elif action == "tomorrow":
        bot.send_message(customer_id, f"📅 Buyurtmangiz #{order_id} ertaga tayyor bo'ladi.")
        bot.answer_callback_query(call.id, "Mijozga ertaga tayyor bo'lishi haqida xabar yuborildi.")
    elif action == "ready":
        if order.get("status") == "ready":
            bot.answer_callback_query(call.id, "Bu buyurtma tayyor deb belgilangan.")
            return
        bot.send_message(customer_id, f"✅ Buyurtmangiz #{order_id} tayyor bo'ldi!", reply_markup=main_keyboard())
        order["status"] = "ready"
        bot.send_message(
            OWNER_CHAT_ID,
            f"✅ Buyurtmangiz #{order_id} tayyor bo'ldi! Mijozga ham xabar yuborildi.",
            reply_markup=main_keyboard(),
        )
        bot.answer_callback_query(call.id, "Mijozga buyurtma tayyorligi yuborildi.")
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None,
        )


@bot.message_handler(content_types=["text", "photo", "document"])
def handle_message(message):
    text = (message.text or "").strip() if message.content_type == "text" else ""
    user_id = message.from_user.id

    if text == BACK_BUTTON:
        user_orders.pop(user_id, None)
        bot.send_message(message.chat.id, "Bosh menyu:", reply_markup=main_keyboard())
        return

    if text in ("💰 Narxlar", "💵 Narxlar"):
        user_orders.pop(user_id, None)
        bot.send_message(
            message.chat.id,
            "💰 Narxlar xizmat turiga qarab belgilanadi. Aniq narx uchun buyurtma yuboring yoki bog'laning: +998 88 311 27 01",
            reply_markup=main_keyboard(),
        )
        return
    if text in ("📞 Bog'lanish", "☎️ Bog'lanish"):
        user_orders.pop(user_id, None)
        bot.send_message(
            message.chat.id,
            "📞 +998 88 311 27 01\nTelegram: @UMIRZOQ_701\n🕘 Ish vaqti: 24/7 | Instagram: https://www.instagram.com/umirzoq_701/",
            reply_markup=main_keyboard(),
        )
        return

    if text in MAIN_MENU:
        options = SUBSERVICES.get(text)
        if options:
            user_orders[user_id] = {"main_button": text, "step": "subservice"}
            bot.send_message(
                message.chat.id,
                f"{MAIN_MENU[text]} bo'limidan keraklisini tanlang:",
                reply_markup=submenu_keyboard(options),
            )
        else:
            begin_order(message, text)
        return

    order = user_orders.get(user_id)
    if order and order.get("step") == "subservice":
        main_button = order["main_button"]
        if text in SUBSERVICES.get(main_button, []):
            order["service"] = MAIN_MENU[main_button]
            order["detail"] = text
            order["photos"] = []
            order["files"] = []
            order["note"] = ""
            order["phone"] = ""
            order["step"] = "media"
            bot.send_message(
                message.chat.id,
                f"Tanlandi: {text}\n\n"
                "Buyurtma namunasi yoki kerakli materialning rasmini/faylini yuboring. "
                "Keyin izoh yozishingiz mumkin. Rasm bo'lmasa, “Davom etish”ni bosing.",
                reply_markup=media_keyboard(),
            )
        else:
            bot.send_message(message.chat.id, "Iltimos, ro'yxatdagi xizmat turini tanlang.")
        return

    if order and order.get("step") == "media":
        if message.content_type == "photo":
            order["photos"].append(message.photo[-1].file_id)
            if message.caption:
                order["note"] = (order["note"] + "\n" + message.caption).strip()
            bot.send_message(
                message.chat.id,
                "Rasm qo'shildi. Yana rasm/fayl yuboring yoki izoh yozing.",
                reply_markup=media_keyboard(),
            )
            return
        if message.content_type == "document":
            order["files"].append((message.document.file_id, message.document.file_name or ""))
            if message.caption:
                order["note"] = (order["note"] + "\n" + message.caption).strip()
            bot.send_message(
                message.chat.id,
                "Fayl qo'shildi. Yana rasm/fayl yuboring yoki izoh yozing.",
                reply_markup=media_keyboard(),
            )
            return
        if text == PHONE_BUTTON:
            order["step"] = "phone"
            bot.send_message(
                message.chat.id,
                "Telefon raqamingizni yozing (masalan, +998901234567). Raqam qoldirish ixtiyoriy; istamasangiz “Davom etish”ni bosing.",
                reply_markup=phone_keyboard(),
            )
            return
        if text == ADD_NOTE_BUTTON:
            order["step"] = "note"
            bot.send_message(message.chat.id, "Buyurtmangiz haqida izohni yozib yuboring:", reply_markup=make_keyboard([]))
            return
        if text == SKIP_BUTTON:
            show_confirmation(message.chat.id, user_id)
            return
        if text:
            order["note"] = text
            show_confirmation(message.chat.id, user_id)
            return

    if order and order.get("step") == "phone":
        if text == SKIP_BUTTON:
            order["phone"] = ""
            show_confirmation(message.chat.id, user_id)
            return
        if text:
            order["phone"] = text
            show_confirmation(message.chat.id, user_id)
            return
        bot.send_message(
            message.chat.id,
            "Telefon raqamingizni matn qilib yozing yoki raqamsiz davom eting.",
            reply_markup=phone_keyboard(),
        )
        return
    if order and order.get("step") == "note":
        if message.content_type in ("photo", "document"):
            if message.content_type == "photo":
                order["photos"].append(message.photo[-1].file_id)
            else:
                order["files"].append((message.document.file_id, message.document.file_name or ""))
            bot.send_message(message.chat.id, "Rasm/fayl qo'shildi. Izohni matn qilib yuboring yoki /cancel bosing.")
            return
        if text == SKIP_BUTTON:
            show_confirmation(message.chat.id, user_id)
            return
        if text:
            order["note"] = text
            show_confirmation(message.chat.id, user_id)
            return
    if order and order.get("step") == "confirm":
        if text == SEND_BUTTON:
            submit_order(message)
            return
        if text == ADD_MEDIA_BUTTON:
            order["step"] = "media"
            bot.send_message(message.chat.id, "Yana rasm yoki fayl yuboring. Tugagach “Davom etish”ni bosing.", reply_markup=media_keyboard())
            return
        if text == ADD_NOTE_BUTTON:
            order["step"] = "note"
            bot.send_message(message.chat.id, "Izohingizni yozing:", reply_markup=make_keyboard([]))
            return
        if text == PHONE_BUTTON:
            order["step"] = "phone"
            bot.send_message(
                message.chat.id,
                "Telefon raqamingizni yozing (masalan, +998901234567). Raqam qoldirish ixtiyoriy; istamasangiz “Davom etish”ni bosing.",
                reply_markup=phone_keyboard(),
            )
            return
        if message.content_type == "photo":
            order["photos"].append(message.photo[-1].file_id)
            show_confirmation(message.chat.id, user_id)
            return
        if message.content_type == "document":
            order["files"].append((message.document.file_id, message.document.file_name or ""))
            show_confirmation(message.chat.id, user_id)
            return
        bot.send_message(message.chat.id, "Buyurtmani yuborish yoki ma'lumotni o'zgartirish uchun tugmalardan foydalaning.", reply_markup=confirm_keyboard())
        return
    bot.send_message(message.chat.id, "Iltimos, avval xizmatni tanlang:", reply_markup=main_keyboard())


async def health_check(request):
    return web.Response(text="Bot ishlayapti", status=200)


app = web.Application()
app.router.add_get("/", health_check)
app.router.add_get("/health", health_check)


def run_bot_polling():
    bot.infinity_polling()


if __name__ == "__main__":
    print("Telegram bot polling va aiohttp server ishga tushmoqda...")
    polling_thread = threading.Thread(
        target=run_bot_polling,
        name="telegram-polling",
        daemon=True,
    )
    polling_thread.start()
    web.run_app(app, host="0.0.0.0", port=PORT)


