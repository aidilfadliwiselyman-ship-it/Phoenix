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
import os
import io
import logging
from collections import defaultdict

from huggingface_hub import InferenceClient

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("8712694616:AAGNGwX_ZW8GcLfOqRPlvU2upjlTOIGABXE")
HF_TOKEN = os.getenv("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")

CHAT_MODEL = os.getenv(
    "CHAT_MODEL",
    "JonathanColetti/Qwen3.8-27B-Uncensored-GGUF"
)

IMAGE_MODEL = os.getenv(
    "IMAGE_MODEL",
    "Shar514/Flux-Uncensored-V2"
)

EDIT_MODEL = os.getenv(
    "EDIT_MODEL",
    "Shar514/Flux-Uncensored-V2"
)

MAX_HISTORY = 12

# ============================================================
# CHECK CONFIG
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN belum ditetapkan.")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN belum ditetapkan.")

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
# HUGGING FACE
# ============================================================

hf = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto",
)

# ============================================================
# MEMORY
# ============================================================

memory = defaultdict(list)


def trim_history(user_id):
    memory[user_id] = memory[user_id][-MAX_HISTORY:]


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Hai! Aku dah aktif.\n\n"
        "Tak perlu command.\n"
        "Cakap sahaja apa yang kau nak.\n\n"
        "Contoh:\n"
        "• Hai, apa khabar?\n"
        "• Terangkan black hole\n"
        "• Buat gambar bandar futuristik\n"
        "• Edit gambar ini jadi gaya anime\n\n"
        "Aku akan cuba faham sendiri."
    )


# ============================================================
# RESET
# ============================================================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    memory[user_id].clear()

    await update.message.reply_text(
        "🧠 Memory perbualan sudah dibersihkan."
    )


# ============================================================
# INTENT DETECTION
# ============================================================

def detect_intent(text):

    t = text.lower().strip()

    image_words = [
        "buat gambar",
        "hasilkan gambar",
        "jana gambar",
        "generate gambar",
        "generate image",
        "create image",
        "buat imej",
        "hasilkan imej",
        "lukiskan",
        "lukis",
        "gambar tentang",
        "gambar seekor",
        "gambar seorang",
        "poster",
        "wallpaper",
    ]

    edit_words = [
        "edit gambar",
        "ubah gambar",
        "tukar gambar",
        "ubah imej",
        "tukar imej",
        "jadikan gambar",
        "jadikan imej",
        "buang latar",
        "tukar latar",
        "ubah background",
    ]

    for word in edit_words:
        if word in t:
            return "edit"

    for word in image_words:
        if word in t:
            return "image"

    return "chat"


# ============================================================
# CHAT
# ============================================================

async def handle_chat(
    update: Update,
    text: str,
):

    user_id = update.effective_user.id

    memory[user_id].append({
        "role": "user",
        "content": text,
    })

    trim_history(user_id)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "Reply naturally and clearly. "
                "The user speaks Malay, so reply in Malay "
                "unless another language is requested."
            ),
        }
    ]

    messages.extend(memory[user_id])

    await update.message.chat.send_action("typing")

    try:

        result = hf.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        reply = result.choices[0].message.content

        if not reply:
            reply = "Maaf, model tidak menghasilkan jawapan."

        memory[user_id].append({
            "role": "assistant",
            "content": reply,
        })

        trim_history(user_id)

        await update.message.reply_text(reply)

    except Exception as e:

        logger.exception("Chat error")

        await update.message.reply_text(
            "❌ Chat AI gagal.\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# IMAGE GENERATION
# ============================================================

async def handle_image(
    update: Update,
    prompt: str,
):

    status = await update.message.reply_text(
        "🎨 Sedang menghasilkan gambar..."
    )

    try:

        result = hf.text_to_image(
            prompt=prompt,
            model=IMAGE_MODEL,
        )

        buffer = io.BytesIO()

        result.save(
            buffer,
            format="PNG",
        )

        buffer.seek(0)

        await status.delete()

        await update.message.reply_photo(
            photo=buffer,
            caption="🎨 Gambar siap."
        )

    except Exception as e:

        logger.exception("Image error")

        await status.edit_text(
            "❌ Gagal menghasilkan gambar.\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# IMAGE EDIT
# ============================================================

async def handle_edit(
    update: Update,
    prompt: str,
):

    message = update.message

    if not message.photo:

        await message.reply_text(
            "Hantar gambar bersama penerangan perubahan "
            "yang kau mahu."
        )

        return

    status = await message.reply_text(
        "🖼️ Sedang mengedit gambar..."
    )

    try:

        photo = message.photo[-1]

        telegram_file = await update.get_bot().get_file(
            photo.file_id
        )

        image_bytes = await telegram_file.download_as_bytearray()

        result = hf.image_to_image(
            image=bytes(image_bytes),
            prompt=prompt,
            model=EDIT_MODEL,
        )

        buffer = io.BytesIO()

        result.save(
            buffer,
            format="PNG",
        )

        buffer.seek(0)

        await status.delete()

        await message.reply_photo(
            photo=buffer,
            caption="🖼️ Gambar telah diedit."
        )

    except Exception as e:

        logger.exception("Edit error")

        await status.edit_text(
            "❌ Gagal mengedit gambar.\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# TEXT MESSAGE ROUTER
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    intent = detect_intent(text)

    logger.info(
        "User %s intent=%s",
        update.effective_user.id,
        intent,
    )

    if intent == "image":

        prompt = text

        await handle_image(
            update,
            prompt,
        )

    elif intent == "edit":

        await handle_edit(
            update,
            text,
        )

    else:

        await handle_chat(
            update,
            text,
        )


# ============================================================
# PHOTO MESSAGE
# ============================================================

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.message

    if not message:
        return

    caption = message.caption or ""

    if not caption:

        await message.reply_text(
            "🖼️ Aku nampak gambar.\n"
            "Beritahu apa yang kau mahu aku buat "
            "dengan gambar ini."
        )

        return

    # Gambar + arahan = edit
    await handle_edit(
        update,
        caption,
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Unhandled exception",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # Hanya command yang kita simpan ialah start/reset
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )

    # Text biasa
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    # Gambar dengan caption
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
        )
    )

    app.add_error_handler(error_handler)

    logger.info(
        "Telegram AI Auto-Router sedang berjalan."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
