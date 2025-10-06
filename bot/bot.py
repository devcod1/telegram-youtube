# bot/bot.py
import sys
import os
import asyncio
import tempfile
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Make repo root importable (upload_to_linkbox.py is in repo root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from upload_to_linkbox import upload_file_to_linkbox  # must be async or sync wrapper

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is missing")

# Helper to run the blocking upload script in background thread if it's sync
async def run_upload_in_thread(youtube_url: str):
    """
    If upload_file_to_linkbox is async, call it directly:
        return await upload_file_to_linkbox(youtube_url)
    If it's sync (blocking), run it in a thread:
        loop.run_in_executor(...)
    """
    # Detect if upload_file_to_linkbox is a coroutine function
    if asyncio.iscoroutinefunction(upload_file_to_linkbox):
        return await upload_file_to_linkbox(youtube_url)
    else:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, upload_file_to_linkbox, youtube_url)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    chat_id = update.effective_chat.id

    if "youtube.com" not in text and "youtu.be" not in text:
        await context.bot.send_message(chat_id, "Please send a YouTube link (watch or youtu.be).")
        return

    # Acknowledge quickly
    status_msg = await context.bot.send_message(chat_id, "✅ Received. Downloading & uploading — I'll reply when finished.")

    try:
        # Run download+upload (either async or sync wrapped)
        link = await run_upload_in_thread(text)

        # Make sure link is short enough
        link_msg = str(link)
        if len(link_msg) > 4000:
            link_msg = link_msg[:4000] + "\n...[truncated]"

        await context.bot.send_message(chat_id, f"✅ Done!\n{link_msg}")

    except Exception as e:
        # Avoid sending huge tracebacks to Telegram
        msg = str(e)
        if len(msg) > 2000:
            msg = msg[:2000] + " ...[truncated]"
        await context.bot.send_message(chat_id, f"❌ Error: {msg}")

async def main():
    # Build application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Run polling but do NOT close the event loop when finished (prevents "Cannot close a running event loop")
    # close_loop=False is the key fix for the RuntimeError you saw.
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    # Directly run main() — Application.run_polling handles internals
    # Do not use asyncio.run(app.run_polling()) here; run_polling() is sufficient.
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # Graceful exit
        pass
