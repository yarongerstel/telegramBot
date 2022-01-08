from telebot import TeleBot, types
import automation_fill
import sys
import datetime
import time

times = []
with open("key.txt", "r") as key:
    API_KEY = key.read()

bot = TeleBot(API_KEY)
user_information = []


@bot.message_handler(['start'])
def msg_start(msg):
    bot.send_message(msg.chat.id, "ברוך הבא")
    bot.send_message(msg.chat.id, "מהו מספר הזהות שלך?")


@bot.message_handler(content_types=['text'])
def msg_handler(msg):
    if len(user_information) == 0:
        while len(msg.text) != 9 or not msg.text.isnumeric():
            bot.send_message(msg.chat.id, "כתוב תז ב-9 ספרות")
            return
        userid = msg.text
        user_information.append(["id", userid])
        bot.send_message(msg.chat.id, "יופי. באיזה שנה נולדת?")

    if len(user_information) == 1:
        while len(msg.text) != 4 or not msg.text.isnumeric():
            bot.send_message(msg.chat.id, "כתוב שנה ב-4 ספרות")
            return
        useryear = msg.text
        user_information.append(["year", useryear])
        bot.send_message(msg.chat.id, "לפני איזה תאריך תרצה את התור?")

    if len(user_information) == 2:

        while len(msg.text) != 10 or not msg.text[:2].isnumeric() or not msg.text[3:5].isnumeric() or not msg.text[
                                                                                                          6:].isnumeric():
            bot.send_message(msg.chat.id, "כתוב בתבנית של : שנה.חודש.יום ")
            return
        d = datetime.datetime(int(msg.text[6:]), int(msg.text[3:5]), int(msg.text[:2]))
        user_information.append(["date", d])

    if len(user_information) == 3:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name) for name
                       in ['נשים', 'אף אוזן גרון', 'אורטופדיה']])
        keyboard.add(*[types.InlineKeyboardButton(text=name, callback_data=name) for name
                       in ['חירורג שד', 'עיניים', 'עור']])
        msg = bot.send_message(msg.chat.id, 'בחר התמחות', reply_markup=keyboard)
        user_information.append(["name", keyboard])

    @bot.callback_query_handler(func=lambda c: True)
    def inline(c):
        flag = True
        bot.send_message(c.message.chat.id, c.data)
        bot.send_message(c.message.chat.id, "מחפש אחר תור קרוב...")
        while (flag):
            date, location, name_doctor, times = automation_fill.run_web(user_information[0][1], user_information[1][1],
                                                                         c.data)
            d = date[-10:]
            the_date = datetime.datetime(int(d[6:]), int(d[3:5]), int(d[:2]))
            # if find queue early print and stop , else keep searching
            if (user_information[2][1] > the_date):
                bot.send_message(c.message.chat.id, date)
                bot.send_message(c.message.chat.id, location)
                bot.send_message(c.message.chat.id, name_doctor)
                for t in times:
                    bot.send_message(c.message.chat.id, t)
                flag = False
            time.sleep(600)

        # strting from the begining.
        user_information.clear()


bot.polling()
