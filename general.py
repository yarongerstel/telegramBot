from telebot import TeleBot, types
import automation_fill
import datetime
import time
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

WAITING_ID = "waiting_id"
WAITING_YEAR = "waiting_year"
WAITING_DATE = "waiting_date"
WAITING_OTP = "waiting_otp"
WAITING_SPECIALTY = "waiting_specialty"
SEARCHING = "searching"

with open("key.txt", "r") as f:
    API_KEY = f.read().strip()

bot = TeleBot(API_KEY)

# Per-user state: {chat_id: {"state": ..., "id": ..., "year": ..., "date": ..., "driver": ..., "stop_event": ...}}
user_data = {}


def _cleanup_user(chat_id):
    """Stop search thread and close browser for this user."""
    data = user_data.pop(chat_id, None)
    if data:
        if "stop_event" in data:
            data["stop_event"].set()
        if "driver" in data:
            try:
                data["driver"].quit()
            except Exception:
                pass
        logger.info(f"[{chat_id}] Cleaned up user session")


@bot.message_handler(commands=["start"])
def msg_start(msg):
    _cleanup_user(msg.chat.id)
    user_data[msg.chat.id] = {"state": WAITING_ID}
    logger.info(f"[{msg.chat.id}] /start")
    bot.send_message(msg.chat.id, "ברוך הבא לבוט תורים של כללית 🏥")
    bot.send_message(msg.chat.id, "מהו מספר הזהות שלך? (9 ספרות)")


@bot.message_handler(commands=["cancel"])
def msg_cancel(msg):
    _cleanup_user(msg.chat.id)
    logger.info(f"[{msg.chat.id}] /cancel")
    bot.send_message(msg.chat.id, "החיפוש בוטל. שלח /start כדי להתחיל מחדש.")


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
        # Start browser login in background, then ask for OTP
        bot.send_message(chat_id, "מתחבר לאתר כללית... ⏳")
        thread = threading.Thread(target=_do_login, args=(chat_id,), daemon=True)
        thread.start()

    elif state == WAITING_OTP:
        otp = msg.text.strip()
        logger.info(f"[{chat_id}] Received OTP")
        bot.send_message(chat_id, "מאמת קוד... ⏳")
        thread = threading.Thread(target=_do_enter_otp, args=(chat_id, otp), daemon=True)
        thread.start()

    elif state == WAITING_SPECIALTY:
        bot.send_message(chat_id, "בחר התמחות מהכפתורים למעלה.")

    elif state == SEARCHING:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="❌ בטל חיפוש", callback_data="__cancel__"))
        bot.send_message(chat_id, "כבר מחפש עבורך...", reply_markup=keyboard)


def _do_login(chat_id):
    """Background thread: open browser and submit login form."""
    data = user_data.get(chat_id)
    if not data:
        return
    try:
        driver = automation_fill.start_login(data["id"], data["year"])
        user_data[chat_id]["driver"] = driver
        user_data[chat_id]["state"] = WAITING_OTP
        bot.send_message(chat_id, "נשלח אליך קוד SMS מכללית — הקלד אותו כאן:")
    except Exception as e:
        logger.error(f"[{chat_id}] Login failed", exc_info=True)
        bot.send_message(chat_id, f"⚠️ שגיאה בהתחברות: {e}\nשלח /start לנסות שוב.")
        _cleanup_user(chat_id)


def _do_enter_otp(chat_id, otp):
    """Background thread: enter OTP and show specialty keyboard."""
    data = user_data.get(chat_id)
    if not data or "driver" not in data:
        bot.send_message(chat_id, "שגיאה — שלח /start להתחיל מחדש.")
        return
    try:
        automation_fill.enter_otp(data["driver"], otp)
        user_data[chat_id]["state"] = WAITING_SPECIALTY

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                       for name in ["נשים", "אף אוזן גרון", "אורטופדיה"]])
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name)
                       for name in ["חירורג שד", "עיניים", "עור"]])
        bot.send_message(chat_id, "התחברת בהצלחה! בחר התמחות:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"[{chat_id}] OTP entry failed", exc_info=True)
        bot.send_message(chat_id, f"⚠️ שגיאה באימות הקוד: {e}\nנסה שוב — הקלד את הקוד:")
        user_data[chat_id]["state"] = WAITING_OTP


@bot.callback_query_handler(func=lambda c: True)
def inline_handler(c):
    chat_id = c.message.chat.id

    if c.data == "__cancel__":
        _cleanup_user(chat_id)
        bot.answer_callback_query(c.id)
        bot.send_message(chat_id, "החיפוש בוטל. שלח /start להתחיל מחדש.")
        return

    if chat_id not in user_data or user_data[chat_id].get("state") != WAITING_SPECIALTY:
        bot.answer_callback_query(c.id)
        return

    specialty = c.data
    stop_event = threading.Event()
    user_data[chat_id]["state"] = SEARCHING
    user_data[chat_id]["stop_event"] = stop_event

    logger.info(f"[{chat_id}] Starting search: specialty={specialty}")
    bot.answer_callback_query(c.id)
    bot.send_message(chat_id, f"מחפש תור ב{specialty}... (שלח /cancel כדי לעצור)")

    thread = threading.Thread(target=search_loop, args=(chat_id, specialty, stop_event), daemon=True)
    thread.start()


def search_loop(chat_id, specialty, stop_event):
    data = user_data.get(chat_id)
    if not data:
        return

    driver = data["driver"]
    deadline = data["date"]

    while not stop_event.is_set():
        try:
            date_str, location, name_doctor, times = automation_fill.search_once(driver, specialty)

            if stop_event.is_set():
                return

            d_part = date_str[-10:]
            parts = d_part.split(".")
            found_date = datetime.datetime(int(parts[2]), int(parts[1]), int(parts[0]))

            if found_date < deadline:
                bot.send_message(chat_id, f"מצאתי תור! 🎉\n📅 {date_str}\n📍 {location}\n👨‍⚕️ {name_doctor}")
                if times:
                    bot.send_message(chat_id, "שעות פנויות:\n" + "\n".join(times))
                _cleanup_user(chat_id)
                return

            bot.send_message(chat_id, f"התור הקרוב ביותר הוא {date_str} — עדיין רחוק מדי. אחפש שוב בעוד 10 דקות.")

        except Exception as e:
            logger.error(f"[{chat_id}] Search error", exc_info=True)
            # If session expired, ask user to re-login
            if "session" in str(e).lower() or "invalid session" in str(e).lower():
                bot.send_message(chat_id, "⚠️ פג תוקף החיבור לכללית. שלח /start להתחבר מחדש.")
                _cleanup_user(chat_id)
                return
            bot.send_message(chat_id, f"⚠️ שגיאה בחיפוש: {e}\nאנסה שוב בעוד 10 דקות. שלח /cancel לעצירה.")

        for _ in range(60):
            if stop_event.is_set():
                return
            time.sleep(10)


bot.polling()
