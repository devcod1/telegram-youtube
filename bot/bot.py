# bot/bot.py
import sys
import os
import traceback
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import asyncio

# allow importing upload_to_linkbox.py from repo root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from upload_to_linkbox import upload_file_to_linkbox  # async function

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is missing")

MAX_TELEGRAM_MSG = 4000

async def safe_send(bot, chat_id: int, text: str):
    """Send text safely (ensure string, truncate, and catch exceptions)."""
    if text is None:
        text = "None"
    # guarantee it's a string
    text = str(text)
    if len(text) > MAX_TELEGRAM_MSG:
        text = text[:MAX_TELEGRAM_MSG - 50] + "\n...[truncated]"
    try:
        return await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        # log to stdout (visible in Actions)
        print("Exception sending Telegram message:", e)
        print(traceback.format_exc())
        # don't re-raise — we don't want unhandled exceptions during error reporting
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()

    if not text or ("youtube.com" not in text and "youtu.be" not in text):
        await safe_send(context.bot, chat_id, "Please send a single YouTube link (no playlists).")
        return

    await safe_send(context.bot, chat_id, "✅ Received. Attempting to download & upload (no cookies). I'll reply when done.")

    try:
        # call the async upload function
        result = await upload_file_to_linkbox(text)

        # defensive: ensure result is a string URL
        if result is None:
            raise RuntimeError("upload_file_to_linkbox returned None")
        if isinstance(result, bool):
            raise RuntimeError(f"upload_file_to_linkbox returned a boolean ({result}) instead of a URL string")

        link_msg = str(result)
        # send final message
        await safe_send(context.bot, chat_id, f"✅ Done!\n{link_msg}")

    except Exception as e:
        # log full traceback to workflow logs for debugging
        tb = traceback.format_exc()
        print("=== Exception in handle_message ===")
        print(tb)

        # user-friendly message
        msg = str(e)
        if "signed-in session" in msg.lower() or "use --cookies" in msg.lower():
            await safe_send(context.bot, chat_id, "❌ This video requires signing in (YouTube blocked anonymous download). I can't download it without cookies/authentication.")
        else:
            # send short version to user
            short = msg
            if len(short) > 1000:
                short = short[:1000] + " ...[truncated]"
            await safe_send(context.bot, chat_id, f"❌ Error: {short}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
