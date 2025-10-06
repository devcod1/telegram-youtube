# bot/bot.py
import sys
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Make repo root importable so we can import upload_to_linkbox from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import your upload logic. It can be either a synchronous function or an async coroutine.
# Expected signature: upload_file_to_linkbox(youtube_url) -> returns str (link) or raises Exception
from upload_to_linkbox import upload_file_to_linkbox

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is missing")

# Helper: call upload function, whether async or sync
async def run_upload(youtube_url: str):
    if asyncio.iscoroutinefunction(upload_file_to_linkbox):
        # upload_file_to_linkbox is async
        return await upload_file_to_linkbox(youtube_url)
    else:
        # upload_file_to_linkbox is blocking sync; run in threadpool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, upload_file_to_linkbox, youtube_url)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    if not text or ("youtube.com" not in text and "youtu.be" not in text):
        await context.bot.send_message(chat_id, "Please send a YouTube link (watch URL or youtu.be).")
        return

    # Acknowledge quickly (short message to avoid flood)
    ack = await context.bot.send_message(chat_id, "✅ Received. Downloading & uploading — I'll reply when finished.")

    try:
        # Run the upload (this will run in async or threadpool as needed)
        link = await run_upload(text)

        # Ensure message is short enough
        link_msg = str(link)
        if len(link_msg) > 4000:
            link_msg = link_msg[:4000] + "\n...[truncated]"

        await context.bot.send_message(chat_id, f"✅ Done!\n{link_msg}")

    except Exception as e:
        # Send short error message
        err = str(e)
        if len(err) > 1500:
            err = err[:1500] + " ...[truncated]"
        await context.bot.send_message(chat_id, f"❌ Error: {err}")

def main():
    """Synchronous entry point that starts polling. Do NOT wrap run_polling in asyncio.run()."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Run polling. close_loop=False prevents run_polling() from closing a loop owned by the environment.
    # This avoids "Cannot close a running event loop" or "This event loop is already running".
    try:
        app.run_polling(close_loop=False)
    except (KeyboardInterrupt, SystemExit):
        # graceful exit
        pass

if __name__ == "__main__":
    main()
