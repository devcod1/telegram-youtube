import os
import time
import requests
import subprocess
from telegram import Bot, Update
from telegram.ext import Updater, MessageHandler, Filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher

LINKBOX_API_TOKEN = os.environ["LINKBOX_API_TOKEN"]
UPLOAD_FOLDER_ID = os.environ.get("LINKBOX_FOLDER_ID", "0")

def handle_message(update, context):
    text = update.message.text
    chat_id = update.message.chat.id

    if "youtube.com" in text or "youtu.be" in text:
        bot.send_message(chat_id, "Received YouTube link. Uploading...")
        # Call GitHub Actions script locally
        try:
            result = subprocess.run(
                ["python", "../upload_to_linkbox.py", text],
                capture_output=True, text=True
            )
            bot.send_message(chat_id, result.stdout)
        except Exception as e:
            bot.send_message(chat_id, f"Error: {str(e)}")
    else:
        bot.send_message(chat_id, "Send a valid YouTube link.")

handler = MessageHandler(Filters.text & (~Filters.command), handle_message)
dispatcher.add_handler(handler)

updater.start_polling()
updater.idle()
