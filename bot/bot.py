import os
import asyncio
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

LINKBOX_FOLDER_ID = os.environ.get("LINKBOX_FOLDER_ID", "0")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat.id

    if "youtube.com" in text or "youtu.be" in text:
        status_msg = await update.message.reply_text("Received YouTube link. Uploading...")

        # Run upload script asynchronously
        proc = await asyncio.create_subprocess_exec(
            "python", "upload_to_linkbox.py", text,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        # Handle long messages
        result_text = stdout.decode().strip() if stdout else "No output."
        if len(result_text) > 4000:
            result_text = result_text[:4000] + "\n...output truncated..."
        
        try:
            await status_msg.edit_text(result_text)
        except Exception:
            # If message can't be edited (same content), just send a new message
            await context.bot.send_message(chat_id, result_text)
    else:
        await update.message.reply_text("Send a valid YouTube link.")

# Start bot
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
