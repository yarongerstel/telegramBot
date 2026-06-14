#!/usr/bin/env python3
"""Personal Assistant Telegram Bot — AI chat, web search, weather."""

import os
import logging
import requests
from telebot import TeleBot
import anthropic
from duckduckgo_search import DDGS

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

def _load(env_var: str, file_name: str) -> str:
    if val := os.getenv(env_var):
        return val
    try:
        return open(file_name).read().strip()
    except FileNotFoundError:
        return ''

BOT_TOKEN     = _load('TELEGRAM_BOT_TOKEN', 'key.txt')
ANTHROPIC_KEY = _load('ANTHROPIC_API_KEY',  'claude_key.txt')

if not BOT_TOKEN:
    raise RuntimeError("Telegram token not found. Set TELEGRAM_BOT_TOKEN or create key.txt")

bot    = TeleBot(BOT_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None

# ── Conversation state ─────────────────────────────────────────────────────────

histories: dict[int, list] = {}
MAX_TURNS = 20

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM = """אתה עוזר אישי חכם ומועיל.
- ענה בעברית כברירת מחדל; עבור לשפת המשתמש אם הוא כותב בשפה אחרת.
- השתמש בכלי search_web כשצריך מידע עדכני, חדשות, מחירים, עובדות ספציפיות, או כל דבר שיכול להשתנות עם הזמן.
- השתמש בכלי get_weather כשמבקשים מזג אוויר.
- ענה בצורה ידידותית, ברורה ותמציתית.
- כשאתה מחפש, ציין בקצרה שאתה מחפש לפני שתציג תוצאות."""

# ── Tool definitions ───────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_web",
        "description": (
            "Search the internet for up-to-date information: news, prices, facts, "
            "people, events, how-to guides, etc. Use this whenever the information "
            "might be recent or you're not sure of the answer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Use the most effective language for the topic."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": "Get current weather conditions and tomorrow's forecast for any city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, preferably in English or transliterated."
                }
            },
            "required": ["city"]
        }
    }
]

# ── Tool implementations ───────────────────────────────────────────────────────

def search_web(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "לא נמצאו תוצאות לחיפוש זה."
        lines = [f"תוצאות חיפוש עבור '{query}':\n"]
        for i, r in enumerate(results, 1):
            body = r.get('body', '')[:300]
            lines.append(f"{i}. {r.get('title', '')}\n{body}\n{r.get('href', '')}\n")
        return "\n".join(lines)
    except Exception as e:
        log.error("search error: %s", e)
        return f"שגיאה בחיפוש: {e}"


def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{requests.utils.quote(city)}?format=j1"
        data = requests.get(url, timeout=10).json()

        cur       = data['current_condition'][0]
        area      = data['nearest_area'][0]
        city_name = area['areaName'][0]['value']
        country   = area['country'][0]['value']

        desc  = cur['weatherDesc'][0]['value']
        temp  = cur['temp_C']
        feels = cur['FeelsLikeC']
        humid = cur['humidity']
        wind  = cur['windspeedKmph']

        lines = [
            f"מזג אוויר ב-{city_name}, {country}:",
            f"מצב: {desc}",
            f"טמפרטורה: {temp}°C (מרגיש כמו {feels}°C)",
            f"לחות: {humid}%  |  רוח: {wind} קמ\"ש",
        ]

        if len(data['weather']) > 1:
            tmr      = data['weather'][1]
            tmr_desc = tmr['hourly'][4]['weatherDesc'][0]['value']
            lines.append(
                f"\nמחר: {tmr_desc}, {tmr['mintempC']}°C – {tmr['maxtempC']}°C"
            )
        return "\n".join(lines)
    except Exception as e:
        log.error("weather error: %s", e)
        return f"לא הצלחתי לקבל מזג אוויר עבור '{city}'. נסה עיר באנגלית."


TOOL_FUNCS = {
    "search_web": lambda inp: search_web(inp["query"]),
    "get_weather": lambda inp: get_weather(inp["city"]),
}

# ── AI chat with tool-use loop ─────────────────────────────────────────────────

def chat(chat_id: int, user_text: str) -> str:
    if not claude:
        return (
            "⚠️ מפתח Anthropic API לא הוגדר.\n"
            "הוסף את ANTHROPIC_API_KEY כמשתנה סביבה, או צור קובץ claude_key.txt עם המפתח."
        )

    hist = histories.setdefault(chat_id, [])
    hist.append({"role": "user", "content": user_text})
    if len(hist) > MAX_TURNS:
        hist[:] = hist[-MAX_TURNS:]

    messages = list(hist)

    for _ in range(6):      # allow up to 6 tool-use rounds
        resp = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        if resp.stop_reason == "tool_use":
            tool_results = []
            for blk in resp.content:
                if blk.type == "tool_use":
                    fn     = TOOL_FUNCS.get(blk.name)
                    result = fn(blk.input) if fn else "כלי לא ידוע"
                    log.info("tool %s(%s) => %.80s…", blk.name, blk.input, result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": blk.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user",      "content": tool_results})
        else:
            answer = "".join(
                blk.text for blk in resp.content if hasattr(blk, "text")
            )
            hist.append({"role": "assistant", "content": answer})
            return answer

    return "מצטער, לא הצלחתי לעבד את הבקשה. נסה שוב."

# ── Message helper ─────────────────────────────────────────────────────────────

def send(chat_id: int, text: str):
    """Send a message; split at 4000 chars; fall back from Markdown to plain."""
    for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)]:
        try:
            bot.send_message(chat_id, chunk, parse_mode='Markdown')
        except Exception:
            bot.send_message(chat_id, chunk)

# ── Handlers ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def on_start(msg):
    send(msg.chat.id,
         "👋 *שלום! אני העוזר האישי שלך.*\n\n"
         "אני יכול לעזור לך עם:\n"
         "🗣 שאלות ושיחות — כתוב לי כל דבר\n"
         "🔍 חיפוש באינטרנט — 'חפש לי...'\n"
         "🌤 מזג אוויר — 'מה מזג האוויר בתל אביב?'\n"
         "📰 חדשות — 'מה קורה היום בישראל?'\n"
         "✍️ כתיבה — מיילים, תרגומים, סיכומים\n\n"
         "/clear לנקות זיכרון השיחה | /help לעזרה\n\n"
         "מה תרצה? 😊")


@bot.message_handler(commands=['help'])
def on_help(msg):
    send(msg.chat.id,
         "📋 *עזרה*\n\n"
         "פשוט כתוב לי מה אתה צריך. לדוגמה:\n\n"
         "• 'מה מזג האוויר בחיפה מחר?'\n"
         "• 'חפש חדשות ספורט'\n"
         "• 'תרגם לאנגלית: אני אוהב פיצה'\n"
         "• 'כתוב לי מייל מקצועי בנושא...'\n"
         "• 'מה ההבדל בין Python ל-JavaScript?'\n\n"
         "*פקודות:*\n"
         "/clear — מחק היסטוריית שיחה (זיכרון חדש)\n"
         "/start — הודעת פתיחה")


@bot.message_handler(commands=['clear'])
def on_clear(msg):
    histories[msg.chat.id] = []
    bot.send_message(msg.chat.id, "✅ היסטוריית השיחה נוקתה. מתחילים מחדש!")


@bot.message_handler(func=lambda m: m.text is not None)
def on_text(msg):
    bot.send_chat_action(msg.chat.id, 'typing')
    try:
        reply = chat(msg.chat.id, msg.text)
        send(msg.chat.id, reply)
    except anthropic.APIError as e:
        log.error("Claude API error: %s", e)
        bot.send_message(msg.chat.id, "⚠️ שגיאה בתקשורת עם ה-AI. נסה שוב.")
    except Exception as e:
        log.error("Unexpected error: %s", e)
        bot.send_message(msg.chat.id, "⚠️ אירעה שגיאה. נסה שוב.")

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    log.info("Personal assistant bot starting…")
    bot.infinity_polling(interval=1, timeout=30)
