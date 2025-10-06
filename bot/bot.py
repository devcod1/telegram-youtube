import sys
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Add root folder to Python path to import upload_to_linkbox
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from upload_to_linkbox import upload_file_to_linkbox

# Telegram bot token from environment variable
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables!")

# Handler for incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if not text:
        await context.bot.send_message(chat_id, "Error: Message text is empty")
        return

    # Only process YouTube links (basic check)
    if "youtube.com/watch" not in text and "youtu.be/" not in text:
        await context.bot.send_message(chat_id, "Please send a valid YouTube link.")
        return

    status_msg = await context.bot.send_message(chat_id, "Received YouTube link. Uploading...")

    try:
        # Call the upload function
        linkbox_url = await upload_file_to_linkbox(text, update, context)

        # Edit message to show success
        await status_msg.edit_text(f"✅ Uploaded to Linkbox successfully:\n{linkbox_url}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to upload:\n{str(e)}")
        # Also log error to chat
        await context.bot.send_message(chat_id, f"Exception: {str(e)}")

# Main function to run the bot
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
