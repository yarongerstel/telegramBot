from telebot import TeleBot, types
import automation_fill
import datetime
import time
import threading

WAITING_ID = "waiting_id"
WAITING_YEAR = "waiting_year"
WAITING_DATE = "waiting_date"
WAITING_SPECIALTY = "waiting_specialty"
SEARCHING = "searching"

with open("key.txt", "r") as f:
    API_KEY = f.read().strip()

bot = TeleBot(API_KEY)

# Per-user state: {chat_id: {"state": ..., "id": ..., "year": ..., "date": ...}}
user_data = {}


def init_user(chat_id):
    # Stop any running search before resetting
    old = user_data.get(chat_id)
    if old and "stop_event" in old:
        old["stop_event"].set()
    user_data[chat_id] = {"state": WAITING_ID}


@bot.message_handler(commands=["start"])
def msg_start(msg):
    init_user(msg.chat.id)
    bot.send_message(msg.chat.id, "ברוך הבא לבוט תורים של כללית 🏥")
    bot.send_message(msg.chat.id, "מהו מספר הזהות שלך? (9 ספרות)")


@bot.message_handler(commands=["cancel"])
def msg_cancel(msg):
    chat_id = msg.chat.id
    data = user_data.get(chat_id)
    if data and "stop_event" in data:
        data["stop_event"].set()
    user_data.pop(chat_id, None)
    bot.send_message(chat_id, "החיפוש בוטל. שלח /start כדי להתחיל מחדש.")


@bot.message_handler(content_types=["text"])
def msg_handler(msg):
    chat_id = msg.chat.id

    if chat_id not in user_data:
        bot.send_message(chat_id, "שלח /start כדי להתחיל")
        return

    state = user_data[chat_id]["state"]

    if state == WAITING_ID:
        if len(msg.text) != 9 or not msg.text.isnumeric():
            bot.send_message(chat_id, "ת.ז. חייבת להיות 9 ספרות בדיוק. נסה שוב:")
            return
        user_data[chat_id]["id"] = msg.text
        user_data[chat_id]["state"] = WAITING_YEAR
        bot.send_message(chat_id, "יופי! באיזו שנה נולדת? (4 ספרות)")

    elif state == WAITING_YEAR:
        if len(msg.text) != 4 or not msg.text.isnumeric():
            bot.send_message(chat_id, "שנה חייבת להיות 4 ספרות. נסה שוב:")
            return
        user_data[chat_id]["year"] = msg.text
        user_data[chat_id]["state"] = WAITING_DATE
        bot.send_message(chat_id, "לפני איזה תאריך תרצה את התור? (פורמט: DD.MM.YYYY)")

    elif state == WAITING_DATE:
        try:
            parts = msg.text.split(".")
            if len(parts) != 3:
                raise ValueError
            d = datetime.datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            bot.send_message(chat_id, "תאריך לא תקין. כתוב בפורמט DD.MM.YYYY (למשל: 31.12.2025)")
            return
        user_data[chat_id]["date"] = d
        user_data[chat_id]["state"] = WAITING_SPECIALTY

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                       for name in ["נשים", "אף אוזן גרון", "אורטופדיה"]])
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                       for name in ["חירורג שד", "עיניים", "עור"]])
        bot.send_message(chat_id, "בחר התמחות:", reply_markup=keyboard)

    elif state == SEARCHING:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ בטל חיפוש", callback_data="__cancel__"))
        bot.send_message(chat_id, "כבר מחפש עבורך...", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda c: True)
def inline_handler(c):
    chat_id = c.message.chat.id

    if c.data == "__cancel__":
        data = user_data.get(chat_id)
        if data and "stop_event" in data:
            data["stop_event"].set()
        user_data.pop(chat_id, None)
        bot.answer_callback_query(c.id)
        bot.send_message(chat_id, "החיפוש בוטל. שלח /start כדי להתחיל חיפוש חדש.")
        return

    if chat_id not in user_data or user_data[chat_id].get("state") != WAITING_SPECIALTY:
        return

    specialty = c.data
    stop_event = threading.Event()
    user_data[chat_id]["state"] = SEARCHING
    user_data[chat_id]["stop_event"] = stop_event

    bot.answer_callback_query(c.id)
    bot.send_message(chat_id, f"מחפש תור ב{specialty}... (שלח /cancel או לחץ ❌ כדי לעצור)")

    thread = threading.Thread(target=search_loop, args=(chat_id, specialty, stop_event), daemon=True)
    thread.start()


def search_loop(chat_id, specialty, stop_event):
    data = user_data.get(chat_id)
    if not data:
        return

    user_id = data["id"]
    year = data["year"]
    deadline = data["date"]

    while not stop_event.is_set():
        try:
            date_str, location, name_doctor, times = automation_fill.run_web(user_id, year, specialty)

            if stop_event.is_set():
                return

            # parse the date returned (last 10 chars are DD.MM.YYYY)
            d_part = date_str[-10:]
            parts = d_part.split(".")
            found_date = datetime.datetime(int(parts[2]), int(parts[1]), int(parts[0]))

            if found_date < deadline:
                bot.send_message(chat_id, f"מצאתי תור! 🎉\n📅 {date_str}\n📍 {location}\n👨‍⚕️ {name_doctor}")
                if times:
                    bot.send_message(chat_id, "שעות פנויות:\n" + "\n".join(times))
                user_data.pop(chat_id, None)
                return

            bot.send_message(chat_id, f"התור הקרוב ביותר הוא {date_str} — עדיין רחוק מדי. אחפש שוב בעוד 10 דקות.")

        except Exception as e:
            bot.send_message(chat_id, f"⚠️ שגיאה בחיפוש: {e}\nאנסה שוב בעוד 10 דקות. שלח /cancel לעצירה.")

        # Sleep in small intervals so cancel takes effect quickly
        for _ in range(60):
            if stop_event.is_set():
                return
            time.sleep(10)


bot.polling()
