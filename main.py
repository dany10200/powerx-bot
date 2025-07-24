import os
import openai
import smtplib
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from email.message import EmailMessage
from collections import defaultdict
from datetime import datetime
from aiohttp import web

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
LOCATION = os.getenv("LOCATION")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

assert BOT_TOKEN, "❌ BOT_TOKEN غير موجود في .env"
assert OPENAI_API_KEY, "❌ OPENAI_API_KEY غير موجود"
assert EMAIL_ADDRESS and EMAIL_PASSWORD, "❌ إعدادات الإيميل ناقصة"
assert WEBHOOK_URL, "❌ WEBHOOK_URL غير معرف"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

user_message_count = defaultdict(int)
user_conversations = defaultdict(list)
MAX_MESSAGES = 20

CLOSING_MESSAGE = "\n📞 لمزيد من المعلومات والاستفسارات يُرجى الاتصال أو إرسال واتساب على الرقم 0597218485"

SYSTEM_PROMPT = f"""
أنت موظف خدمة عملاء ذكي في مركز PowerX في السعودية، ترد باللهجة السعودية باحتراف تسويقي وبأسلوب ودود، وتستخدم رموز خفيفة وقت الحاجة (🚗✨👌).
تجاوب حسب سؤال العميل وتعرض الخدمات والباقات عند الحاجة، بدون تكرار، ولا ترد بنفس الرد مرتين.
ما تستخدم نفس الجملة دائمًا، وتختم فقط آخر رسالة بعد 20 رسالة بـ: {CLOSING_MESSAGE}

الخدمات:
- تلميع خارجي: 300 ريال – بدون ضمان.
- تلميع داخلي: 300 ريال – بدون ضمان.
- نانو سيراميك + تلميع خارجي: 950 ريال – ضمان 3 سنوات مع مراجعات مجانية كل 6 شهور.
- تظليل حراري أمريكي: 920 ريال – ضمان 6 سنوات – 99% UV / 99% IR / 65% TSER.
- حماية PPF XPEL:
   * نصف الكبوت + المقدمة: 1400 ريال
   * كبوت كامل + المقدمة: 1950 ريال
   * كل الحمايات تشمل: الكبوت، الصدام، الرفارف، المرايات، المقابض – بضمان 6 سنوات.
الموقع: {LOCATION}الدمام حي الزهور
الباقات:
- باقة تيربو – 1890 ريال: حماية نص كبوت + تظليل + نانو سيراميك + نانو داخلي.
- الباقة الماسية – 2500 ريال: حماية كاملة + تظليل + نانو داخلي + نانو جنوط.
- باقة VIP – 7000 ريال: تغليف كامل + تظليل + نانو داخلي.
الأسعار تختلف حسب حجم السيارة. الأرضيات تُسعر من المشرف.
"""

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

@dp.message_handler(commands=["start", "help"])
async def start(message: types.Message):
    await message.reply("هلا فيك معاك فريق PowerX 👋 اسألنا عن خدماتنا أو الأسعار، ونساعدك على طول!")

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

    text = message.text.lower()
    if "موقع" in text or "وين" in text:
        await message.reply(f"📍 موقعنا: {LOCATION}")
        return

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": "user", "content": message.text}]
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

# ✅ Webhook setup
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

# ✅ Webhook endpoint
async def handle_webhook(request):
    body = await request.json()
    update = types.Update.to_object(body)
    await dp.process_update(update)
    return web.Response()

async def main():
    await on_startup(dp)
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/", lambda request: web.Response(text="PowerX bot is alive ✅"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

if __name__ == "__main__":
    asyncio.run(main())
