# עוזר אישי — בוט טלגרם

בוט שרץ 24/7 ועוזר לך עם שיחות, חיפוש באינטרנט, מזג אוויר, חדשות וכל שאלה שתרצה.

---

## מה הבוט יודע לעשות

- **שיחה חופשית** — שאל כל שאלה, בקש הסבר, קבל עצות
- **חיפוש באינטרנט** — מידע עדכני, חדשות, מחירים, עובדות
- **מזג אוויר** — טמפרטורה, לחות, תחזית למחר לכל עיר בעולם
- **כתיבה** — מיילים, תרגומים, סיכומים, ניסוח מחדש
- **זיכרון שיחה** — זוכר את ההיסטוריה ומשיב בהקשר

---

## הגדרה ראשונית

### דרישות
- Python 3.8 ומעלה
- מפתח Telegram Bot (`key.txt` או `TELEGRAM_BOT_TOKEN`)
- מפתח Anthropic API (`claude_key.txt` או `ANTHROPIC_API_KEY`)

### התקנה

```bash
pip install -r requirements.txt
```

### קבצי מפתחות (מקומי)

```bash
echo "TOKEN_FROM_BOTFATHER" > key.txt
echo "sk-ant-..." > claude_key.txt
```

### משתני סביבה (פריסה לענן)

```
TELEGRAM_BOT_TOKEN=TOKEN_FROM_BOTFATHER
ANTHROPIC_API_KEY=sk-ant-...
```

---

## הפעלה מקומית

```bash
python general.py
```

---

## פריסה לענן (תמיד דולק)

### Render.com

1. צור חשבון ב-[render.com](https://render.com)
2. **New → Web Service** → חבר לגיטהאב
3. הגדרות:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python general.py`
   - **Environment Variables:** `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`
4. Deploy — הבוט ירוץ 24/7

### Railway.app

1. צור חשבון ב-[railway.app](https://railway.app)
2. **New Project → GitHub Repo**
3. הוסף משתני סביבה
4. השירות יתחיל אוטומטית

---

## שימוש

| פקודה | מה עושה |
|-------|---------|
| `/start` | הודעת פתיחה |
| `/help` | רשימת יכולות |
| `/clear` | מחיקת היסטוריית שיחה |
| כתיבה חופשית | שיחה, חיפוש, מזג אוויר |

**דוגמאות:**
- `מה מזג האוויר בירושלים מחר?`
- `חפש חדשות ספורט`
- `תרגם לאנגלית: טוב מאוד`
- `כתוב לי מייל מקצועי בנושא ביטול פגישה`

---

## מבנה הקבצים

```
telegramBot/
├── general.py        # הבוט הראשי
├── requirements.txt  # תלויות Python
├── .env.example      # תבנית משתני סביבה
├── key.txt           # טוקן טלגרם (לא ב-git)
├── claude_key.txt    # מפתח Anthropic (לא ב-git)
└── README.md
```
