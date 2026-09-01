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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

CHAT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

IMAGE_MODEL = os.getenv(
    "IMAGE_MODEL",
    "darknight9121/FLUX.2-klein-base-9B-bucket-uncensored"
)

EDIT_MODEL = os.getenv(
    "EDIT_MODEL",
    "darknight9121/FLUX.2-klein-base-9B-bucket-uncensored"
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

client = InferenceClient(
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
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Hai! Aku dah aktif.\n\n"
        "Tak perlu command untuk guna AI.\n"
        "Cakap sahaja apa yang kau nak.\n\n"
        "Contoh:\n"
        "• Hai bro\n"
        "• Terangkan black hole\n"
        "• Buat gambar bandar futuristik\n"
        "• Edit gambar ini jadi gaya anime\n\n"
        "Aku akan cuba faham sendiri.\n\n"
        "/reset = kosongkan memory"
    )


# ============================================================
# /RESET
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

async def handle_chat(update: Update, text: str):

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

        result = client.chat_completion(
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
            "❌ Chat AI gagal.\n\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# IMAGE GENERATION
# ============================================================

async def handle_image(update: Update, prompt: str):

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
            "❌ Gagal menghasilkan gambar.\n\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# IMAGE EDIT
# ============================================================

async def handle_edit(update: Update, prompt: str):

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

        telegram_file = await context.bot.get_file(
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
            "❌ Gagal mengedit gambar.\n\n"
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# TEXT ROUTER
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
        "User %s -> %s",
        update.effective_user.id,
        intent,
    )

    if intent == "image":

        await handle_image(
            update,
            text,
        )

    elif intent == "edit":

        # Untuk teks sahaja, minta gambar.
        await update.message.reply_text(
            "🖼️ Hantar gambar bersama arahan perubahan "
            "yang kau mahu."
        )

    else:

        await handle_chat(
            update,
            text,
        )


# ============================================================
# PHOTO ROUTER
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
            "Beritahu apa yang kau mahu aku ubah."
        )

        return

    status = await message.reply_text(
        "🖼️ Sedang memproses gambar..."
    )

    try:

        photo = message.photo[-1]

        telegram_file = await context.bot.get_file(
            photo.file_id
        )

        image_bytes = await telegram_file.download_as_bytearray()

        result = hf.image_to_image(
            image=bytes(image_bytes),
            prompt=caption,
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
            caption="🖼️ Siap."
        )

    except Exception as e:

        logger.exception("Image edit error")

        await status.edit_text(
            "❌ Image editing gagal.\n\n"
            f"{type(e).__name__}: {e}"
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

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    app.add_error_handler(error_handler)

    logger.info(
        "🤖 Telegram + Hugging Face Auto AI started."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
