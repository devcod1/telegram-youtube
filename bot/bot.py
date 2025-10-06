import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Environment variables
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
LINKBOX_API_TOKEN = os.environ["LINKBOX_API_TOKEN"]
UPLOAD_FOLDER_ID = os.environ.get("LINKBOX_FOLDER_ID", "0")

# Async handler for messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat.id

    if "youtube.com" in text or "youtu.be" in text:
        await context.bot.send_message(chat_id, "Received YouTube link. Uploading...")
        try:
            # Call the upload script
            result = subprocess.run(
                ["python", "../upload_to_linkbox.py", text],
                capture_output=True, text=True
            )
            await context.bot.send_message(chat_id, result.stdout)
        except Exception as e:
            await context.bot.send_message(chat_id, f"Error: {str(e)}")
    else:
        await context.bot.send_message(chat_id, "Send a valid YouTube link.")

# Main
if __name__ == "__main__":
    # Build the application and start polling
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
