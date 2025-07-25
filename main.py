import os
import asyncio
import openai
import smtplib
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from flask import Flask, request
from email.message import EmailMessage
from collections import defaultdict
from datetime import datetime

# تحميل متغيرات البيئة
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
LOCATION = os.getenv("LOCATION")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

assert BOT_TOKEN, "❌ BOT_TOKEN غير موجود"
assert OPENAI_API_KEY, "❌ OPENAI_API_KEY غير موجود"
assert EMAIL_ADDRESS and EMAIL_PASSWORD, "❌ إعدادات الإيميل ناقصة"
assert WEBHOOK_URL, "❌ WEBHOOK_URL ناقص"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

user_message_count = defaultdict(int)
user_conversations = defaultdict(list)
MAX_MESSAGES = 25

CLOSING_MESSAGE = "\n📞 لمزيد من المعلومات والاستفسارات يُرجى الاتصال أو إرسال واتساب على الرقم 0597218485"

SYSTEM_PROMPT = """
أنت تمثل مركز PowerX في الدمام، وتعمل كمندوب مبيعات ذكي محترف. وظيفتك الرد على العملاء باللهجة السعودية، بأسلوب تسويقي واقعي، ودود، احترافي، ومقنع.
... (تم اختصار النظام هنا للمساحة – استخدم النص الكامل من كودك)
"""

# إرسال المحادثة عبر الإيميل
def send_email(user_id, messages):
    try:
        msg = EmailMessage()
        msg["Subject"] = f"محادثة عميل ({user_id}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg.set_content("\n\n".join(messages))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ تم إرسال المحادثة إلى الإيميل بنجاح (ID: {user_id})")
    except Exception as e:
        print(f"❌ فشل إرسال الإيميل: {e}")

# أوامر /start و /help
@dp.message_handler(commands=["start", "help"])
async def start(message: types.Message):
    await message.reply("هلا فيك معاك فريق PowerX 👋 اسألنا عن خدماتنا أو الأسعار، ونساعدك على طول!")

# الردود العامة
@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    if not message.text or message.text.strip() == "":
        await message.reply("📝 أرسل لنا سؤالك أو استفسارك بشكل واضح.")
        return

    if len(message.text) > 500:
        await message.reply("🛑 الرسالة طويلة جدًا، ممكن تختصر شوي؟")
        return

    user_message_count[user_id] += 1

    if user_message_count[user_id] > MAX_MESSAGES:
        await message.reply("🚫 وصلت الحد الأقصى من الرسائل المسموح بها.")
        return

    if "موقع" in message.text.lower() or "وين" in message.text.lower():
        await message.reply(f"📍 موقعنا: {LOCATION}")
        return

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ]
        user_conversations[user_id].append(f"👤 {message.text}")

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.6,
            max_tokens=250
        )

        reply = response["choices"][0]["message"]["content"].strip()
        if not reply:
            reply = "🤖 ما قدرت أفهمك، ممكن تعيد سؤالك؟"

        user_conversations[user_id].append(f"🤖 {reply}")
        await message.reply(reply)

        if user_message_count[user_id] == MAX_MESSAGES:
            await message.reply(CLOSING_MESSAGE)
            send_email(user_id, user_conversations[user_id])
            del user_message_count[user_id]
            del user_conversations[user_id]

    except Exception as e:
        print(f"[ERROR] {e}")
        await message.reply(f"⚠️ صار خطأ: {str(e)}")

# إعداد Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🤖 PowerX Bot is running!"

@app.route('/webhook', methods=["POST"])
async def webhook():
    try:
        update = types.Update(**request.get_json(force=True))
        await dp.process_update(update)
    except Exception as e:
        print(f"[Webhook Error] {e}")
    return "ok"

# إعداد Webhook عند التشغيل
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL + "/webhook")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
