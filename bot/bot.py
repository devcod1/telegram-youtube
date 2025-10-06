# bot/bot.py
import sys
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import asyncio

# allow importing upload_to_linkbox.py from repo root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from upload_to_linkbox import upload_file_to_linkbox  # async function

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is missing")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    if not text or ("youtube.com" not in text and "youtu.be" not in text):
        await context.bot.send_message(chat_id, "Please send a single YouTube link (no playlists).")
        return

    # Acknowledge quickly
    await context.bot.send_message(chat_id, "✅ Received. Attempting to download & upload (no cookies). I'll reply when done.")

    try:
        # Call the async upload function (downloads then uploads)
        link = await upload_file_to_linkbox(text)

        # Ensure message length safe
        link_msg = str(link)
        if len(link_msg) > 4000:
            link_msg = link_msg[:4000] + "\n...[truncated]"

        await context.bot.send_message(chat_id, f"✅ Done!\n{link_msg}")

    except Exception as e:
        msg = str(e)
        if len(msg) > 1500:
            msg = msg[:1500] + " ...[truncated]"
        # Provide a friendly, actionable message for auth-required errors
        if "requires a signed-in session" in msg.lower() or "use --cookies" in msg.lower():
            await context.bot.send_message(chat_id, "❌ This video requires signing in (YouTube blocked anonymous download). I can't download it without cookies/authentication.")
        else:
            await context.bot.send_message(chat_id, f"❌ Error: {msg}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Important: prevent closing the environment's event loop
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
