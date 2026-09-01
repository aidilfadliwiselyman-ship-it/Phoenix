import os
import logging

from google import genai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN = os.getenv"8712694616:AAGNGwX_ZW8GcLfOqRPlvU2upjlTOIGABXE"
GEMINI_API_KEY = os.getenv"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"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN belum ditetapkan.")

if not GEMINI_API_KEY:
    raise RuntimeError("HF_TOKEN belum ditetapkan.")

client = genai.Client(api_key=HF_TOKEN)

# Simpan sejarah chat sementara
chat_history = {}

MAX_MESSAGES = 10


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot AI sudah aktif!\n\n"
        "Hantar apa sahaja mesej untuk berbual dengan AI.\n\n"
        "Contoh:\n"
        "• Hai!\n"
        "• Terangkan black hole\n"
        "• Buatkan idea cerita sci-fi"
    )


# =========================
# CHAT
# =========================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    message = update.message.text

    if user_id not in chat_history:
        chat_history[user_id] = []

    history = chat_history[user_id]

    history.append({
        "role": "user",
        "text": message,
    })

    # Hadkan memory
    if len(history) > MAX_MESSAGES:
        history[:] = history[-MAX_MESSAGES:]

    conversation = ""

    for item in history:
        if item["role"] == "user":
            conversation += f"User: {item['text']}\n"
        else:
            conversation += f"Assistant: {item['text']}\n"

    await update.message.chat.send_action("typing")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation,
        )

        reply = response.text

        history.append({
            "role": "assistant",
            "text": reply,
        })

        if len(history) > MAX_MESSAGES:
            history[:] = history[-MAX_MESSAGES:]

        await update.message.reply_text(reply)

    except Exception as e:
        logging.exception("Gemini error")

        await update.message.reply_text(
            "❌ Gemini mengalami ralat.\n\n"
            f"{type(e).__name__}: {e}"
        )


# =========================
# MAIN
# =========================

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat,
        )
    )

    print("🤖 Bot sedang berjalan...")

    app.run_polling()


if __name__ == "__main__":
    main()
