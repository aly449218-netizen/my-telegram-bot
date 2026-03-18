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
    "format": "bestaudio/best",
    "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
    "ffmpeg_location": "/usr/bin/ffmpeg",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
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

            if mode == "audio":
                filename = filename.rsplit(".", 1)[0] + ".mp3"

            return True, filename
    except Exception as e:
        return False, str(e)

# ────────────────
# 📩 start
# ────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    url = update.message.text
    platform = detect_platform(url)

    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("🎬 فيديو", callback_data="video")],
        [InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data="audio")]
    ]

    await update.message.reply_text(
        f"📥 تم اكتشاف: {platform}\n\nاختر نوع التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ────────────────
# 🎛️ الاختيارات
# ────────────────
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

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
            await query.message.reply_audio(audio=open(result, "rb"))
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

    print("✅ Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
