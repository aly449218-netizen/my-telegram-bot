import os
import logging
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

# ─────────────────────────────
# ⚙️ الإعدادات
# ─────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR     = "downloads"
COOKIES_FILE     = "com_cookies.txt"
REQUIRED_CHANNEL = "@ixm_iii"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ─────────────────────────────
# 🌐 Flask (مطلوب لـ Railway)
# ─────────────────────────────
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

# ─────────────────────────────
# ✅ التحقق من الاشتراك
# ─────────────────────────────
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

async def check_subscription(update, context):
    if await is_subscribed(update.effective_user.id, context):
        return True

    keyboard = [[
        InlineKeyboardButton("📢 اشترك", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}"),
        InlineKeyboardButton("✅ تحقق", callback_data="check_sub"),
    ]]
    await update.message.reply_text(
        "اشترك بالقناة أولاً",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return False

# ─────────────────────────────
# 🔽 تنزيل الفيديو
# ─────────────────────────────
def download_video(url):
    ydl_opts = {
        "format": "best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return True, filename
    except Exception as e:
        return False, str(e)

# ─────────────────────────────
# 📩 الأوامر
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return
    await update.message.reply_text("ارسل رابط الفيديو")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return

    url = update.message.text
    await update.message.reply_text("⏳ جاري التحميل...")

    success, result = download_video(url)

    if not success:
        await update.message.reply_text(f"❌ خطأ:\n{result}")
        return

    try:
        await update.message.reply_video(video=open(result, "rb"))
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ بالإرسال: {e}")
    finally:
        if os.path.exists(result):
            os.remove(result)

# ─────────────────────────────
# 🚀 تشغيل البوت
# ─────────────────────────────
def main():
    import threading
    threading.Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    print("✅ Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
