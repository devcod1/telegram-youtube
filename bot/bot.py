import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat.id

    if "youtube.com" in text or "youtu.be" in text:
        await context.bot.send_message(chat_id, "Received YouTube link. Uploading...")

        try:
            # Run upload script and capture both stdout and stderr
            result = subprocess.run(
                ["python", "../upload_to_linkbox.py", text],
                capture_output=True, text=True
            )

            output = result.stdout.strip()
            error_output = result.stderr.strip()

            if output:
                await context.bot.send_message(chat_id, output)
            elif error_output:
                await context.bot.send_message(chat_id, f"Error: {error_output}")
            else:
                await context.bot.send_message(chat_id, "Error: upload script returned nothing.")
        except Exception as e:
            await context.bot.send_message(chat_id, f"Exception: {str(e)}")
    else:
        await context.bot.send_message(chat_id, "Send a valid YouTube link.")

if __name__ == "__main__":
    from telegram.ext import ApplicationBuilder, MessageHandler, filters

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
