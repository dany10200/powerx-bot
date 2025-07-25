import os
import openai
import smtplib
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv
from email.message import EmailMessage
from collections import defaultdict
from datetime import datetime
from aiohttp import web

# تحميل متغيرات البيئة
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
LOCATION = os.getenv("LOCATION")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثل: https://powerx-bot.onrender.com

# تحقق من المتغيرات
assert BOT_TOKEN, "❌ BOT_TOKEN غير موجود"
assert OPENAI_API_KEY, "❌ OPENAI_API_KEY غير موجود"
assert EMAIL_ADDRESS and EMAIL_PASSWORD, "❌ إعدادات الإيميل ناقصة"
assert WEBHOOK_URL, "❌ WEBHOOK_URL ناقص، أضفه في .env"

# تهيئة البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

# تتبع المستخدمين
user_message_count = defaultdict(int)
user_conversations = defaultdict(list)
MAX_MESSAGES = 25

# رسالة ختامية
CLOSING_MESSAGE = "\n📞 لمزيد من المعلومات والاستفسارات يُرجى الاتصال أو إرسال واتساب على الرقم 0597218485"

# النظام الأساسي
SYSTEM_PROMPT = f"""
أنت تمثل مركز PowerX في الدمام، وتعمل كمندوب مبيعات ذكي محترف. وظيفتك الرد على العملاء باللهجة السعودية، بأسلوب تسويقي واقعي، ودود، احترافي، ومقنع.

### 💡 تعليمات الرد:
- جاوب على حسب السؤال بدقة: إذا السؤال عن باقات، لا تذكر خدمات مفردة. وإذا سأل عن خدمة وحدة، لا تخلط مع باقة.
- لا تكرر نفس الرد مرتين، ونوّع في أسلوبك بين العميل والآخر.
- خلك محفز دائمًا، وافهم العميل: هل هو مهتم بالتفاصيل؟ ولا يبي عرض مباشر؟
- لو سألك العميل عن شي ما تعرفه (زي خدمة غير موجودة أو استفسار مش واضح)، لا تحاول تتفلسف، قله:
  👉 "ممكن تتواصل معنا مباشر على الرقم 0597218485 وراح نساعدك أكثر"
- الرقم الرسمي لخدمة العملاء هو: **0597218485**، خزّنه عندك واستخدمه دايمًا للرد.

---

### 🕒 أوقات العمل:
من **الساعة 1 ظهرًا إلى 10 مساءً**  
من **السبت إلى الخميس** – الجمعة إجازة

---

### 📍 موقعنا:
الدمام – حي الزهور

---

### 🧼 الخدمات المفردة:

- **تلميع خارجي** – 300 ريال (بدون ضمان)
- **تلميع داخلي** – 300 ريال (بدون ضمان)
- **نانو سيراميك + تلميع خارجي** – 950 ريال  
  🔒 ضمان 3 سنوات + مراجعات مجانية كل 6 شهور
- **تظليل حراري أمريكي** – 920 ريال  
  🔒 ضمان 6 سنوات – يعزل 99% UV و IR
- **حماية PPF XPEL أصلية**:  
  - نصف الكبوت + المقدمة: 1400 ريال  
  - كبوت كامل + المقدمة: 1950 ريال  
  ✅ تشمل: الكبوت، الصدام، الرفارف، المرايات، المقابض – بضمان 6 سنوات

---

### 💎 الباقات:

- **باقة تيربو – 1890 ريال**  
  حماية نص كبوت + تظليل + نانو سيراميك + نانو داخلي  
  💬 مناسبة للسيارات اللي تمشي كثير وتبي حماية ذكية بسعر ممتاز

- **الباقة الماسية – 2500 ريال**  
  حماية كاملة + تظليل + نانو داخلي + نانو جنوط  
  💬 تعطيك حماية من كل الجهات ولمسة فخامة

- **باقة VIP – 7000 ريال**  
  تغليف كامل PPF + تظليل + نانو داخلي  
  💬 أقوى باقة، مثالية للسيارات الجديدة أو اللي تبي أفضل حماية ممكنة

---

### ⚠️ تنبيهات مهمة:
- الأسعار **تقديرية**، وتختلف حسب **حجم السيارة** (سيدان، SUV، كبيرة جدًا).
- الأرضيات **لا تدخل في السعر**، ويتم تسعيرها من قبل المشرف.
- كل المواد **أصلية ومعتمدة** (XPEL، نانو، تظليل أمريكي حراري).
"""

# إرسال المحادثة بالبريد
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
        print(f"✅ تم إرسال المحادثة إلى الإيميل (ID: {user_id})")
    except Exception as e:
        print(f"❌ فشل الإرسال: {e}")

# أوامر البداية
@dp.message_handler(commands=["start", "help"])
async def start(message: types.Message):
    await message.reply("هلا فيك معاك فريق PowerX 👋 اسألنا عن خدماتنا أو الأسعار، ونساعدك على طول!")

# التعامل مع الرسائل
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
        await message.reply("🚫 وصلت الحد الأقصى من الرسائل.")
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

# إعداد Webhook
WEBHOOK_PATH = "/webhook"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 10000))

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    print(f"✅ Webhook تم تفعيله على {WEBHOOK_URL + WEBHOOK_PATH}")

async def on_shutdown(app):
    print("🔻 إيقاف البوت...")
    await bot.delete_webhook()

# UptimeRobot check endpoint
async def health_check(request):
    return web.Response(text="🤖 PowerX Bot (Webhook) is live.")

# التشغيل
if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", health_check)

    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        web_app=app
    )
