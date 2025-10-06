# bot/bot.py
import sys
import os
import traceback
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import asyncio

# allow importing upload_to_linkbox.py from repo root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from upload_to_linkbox import upload_file_to_linkbox  # MUST return string or raise

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is missing")

MAX_LEN = 4000

async def safe_send(bot, chat_id: int, text):
    """Convert anything to a safe string, truncate, and send. Catch and log exceptions."""
    try:
        if text is None:
            text = "None"
        # Force to string (this prevents 'text must be False' as False -> 'False')
        text = str(text)
        if len(text) > MAX_LEN:
            text = text[:MAX_LEN - 40] + "\n...[truncated]"
        return await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        # Log (visible in GitHub Actions)
        print("Exception while sending message to Telegram:", repr(e))
        print(traceback.format_exc())
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    raw_text = getattr(update.message, "text", "")
    text = (raw_text or "").strip()

    if not chat_id:
        print("No chat_id available in update; skipping.")
        return

    if not text or ("youtube.com" not in text and "youtu.be" not in text):
        await safe_send(context.bot, chat_id, "Please send a valid single YouTube link (no playlists).")
        return

    # Acknowledge quickly
    await safe_send(context.bot, chat_id, "✅ Received. Attempting to download & upload (no cookies). I'll reply when done.")

    try:
        # call upload function; it's async in our repo
        link = await upload_file_to_linkbox(text)

        # Defensive checks: ensure we got a non-empty string
        if link is None:
            raise RuntimeError("upload_file_to_linkbox returned None instead of a link.")
        if isinstance(link, bool):
            raise RuntimeError(f"upload_file_to_linkbox returned a boolean ({link}) instead of a link string.")
        link_str = str(link).strip()
        if not link_str:
            raise RuntimeError("upload_file_to_linkbox returned an empty string.")

        await safe_send(context.bot, chat_id, f"✅ Uploaded to LinkBox:\n{link_str}")

    except Exception as e:
        # Log full traceback to workflow logs for debugging
        print("=== Exception during upload flow ===")
        tb = traceback.format_exc()
        print(tb)

        # Friendly message to user
        msg = str(e)
        if len(msg) > 1200:
            msg = msg[:1200] + " ...[truncated]"
        # If it's an auth/cookies issue, give actionable hint
        lower = msg.lower()
        if "requires a signed-in session" in lower or "use --cookies" in lower or "sign in to confirm" in lower:
            await safe_send(context.bot, chat_id, "❌ This video requires signing in (YouTube blocked anonymous download). I can't download it without cookies/authentication.")
        else:
            await safe_send(context.bot, chat_id, f"❌ Error: {msg}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Run polling without closing loop (prevents runtime loop issues in Actions)
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
