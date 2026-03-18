import os
import logging
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import yt_dlp

# ────────────────
# ⚙️ إعدادات
# ────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
REQUIRED_CHANNEL = "@ixm_iii"  # ← غير اسم القناة هنا

logging.basicConfig(level=logging.INFO)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ────────────────
# 🌐 Flask (Railway)
# ────────────────
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot Running 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

# ────────────────
# ✅ التحقق من الاشتراك
# ────────────────
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def check_subscription(update, context):
    if await is_subscribed(update.effective_user.id, context):
        return True

    keyboard = [[
        InlineKeyboardButton("📢 اشترك بالقناة", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}"),
        InlineKeyboardButton("✅ تحقق", callback_data="check_sub"),
    ]]

    await update.message.reply_text(
        "⚠️ لازم تشترك بالقناة أولاً",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return False

# ────────────────
# 🔍 تحديد المنصة
# ────────────────
def detect_platform(url):
    if "youtube" in url or "youtu.be" in url:
        return "YouTube"
    elif "tiktok" in url:
        return "TikTok"
    elif "instagram" in url:
        return "Instagram"
    return "Unknown"

# ────────────────
# ⬇️ تحميل
# ────────────────
def download(url, mode="video"):
    if mode == "audio":
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        }
    else:
        ydl_opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return True, filename
    except Exception as e:
        return False, str(e)

# ────────────────
# 📩 start
# ────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return

    await update.message.reply_text(
       "👋 هلا بيك!\n\n"
        "📌 أرسل رابط الفيديو وأنا أنزله لك\n"
        "🎵 أو أستخرج الصوت MP3\n\n"
        "🚀 يدعم:\nYouTube | TikTok | Instagram"
    )

# ────────────────
# 🔗 استقبال الرابط
# ────────────────
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return

    url = update.message.text
    platform = detect_platform(url)

    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("🎬 فيديو", callback_data="video")],
        [InlineKeyboardButton("🎵 صوت فقط", callback_data="audio")]
    ]

    await update.message.reply_text(
        f"📥 المنصة: {platform}\n\nاختر:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ────────────────
# 🔄 تحقق الاشتراك
# ────────────────
async def handle_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await is_subscribed(update.effective_user.id, context):
        await query.edit_message_text("✅ تم التحقق! أرسل الرابط الآن")
    else:
        await query.edit_message_text("❌ بعدك ما مشترك")

# ────────────────
# 🎛️ الاختيارات
# ────────────────
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_subscribed(update.effective_user.id, context):
        await query.edit_message_text("❌ لازم تشترك أول")
        return

    url = context.user_data.get("url")

    if not url:
        await query.edit_message_text("❌ أرسل الرابط مرة ثانية")
        return

    mode = query.data

    await query.edit_message_text("⏳ جاري التحميل...")

    success, result = download(url, mode)

    if not success:
        await query.message.reply_text(f"❌ خطأ:\n{result}")
        return

    try:
        if mode == "audio":
            await query.message.reply_document(document=open(result, "rb"))
        else:
            await query.message.reply_video(video=open(result, "rb"))
    except Exception as e:
        await query.message.reply_text(f"❌ خطأ بالإرسال: {e}")
    finally:
        if os.path.exists(result):
            os.remove(result)

# ────────────────
# 🚀 تشغيل
# ────────────────
def main():
    import threading
    threading.Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_choice))
    app.add_handler(CallbackQueryHandler(handle_check_sub, pattern="check_sub"))

    print("✅ Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
