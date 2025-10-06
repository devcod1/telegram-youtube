import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import asyncio

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat.id

    if "youtube.com" in text or "youtu.be" in text:
        # Step 1: Send initial message
        status_msg = await context.bot.send_message(chat_id, "Received YouTube link. Starting download...")

        try:
            # Step 2: Run upload script with periodic message
            process = subprocess.Popen(
                ["python", "upload_to_linkbox.py", text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Poll output line by line
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    # Optionally update status every 3–5 lines
                    if any(keyword in line.lower() for keyword in ["downloading", "uploading"]):
                        await status_msg.edit_text(line.strip())

            stdout, stderr = process.communicate()

            # Step 3: Only send the final LinkBox link
            link_lines = [line for line in stdout.splitlines() if "https://www.linkbox.to/s/" in line]
            if link_lines:
                await context.bot.send_message(chat_id, f"✅ Upload finished!\n{link_lines[-1]}")
            elif stderr:
                await context.bot.send_message(chat_id, f"Error:\n{stderr}")
            else:
                await context.bot.send_message(chat_id, "Error: Upload script returned nothing.")

        except Exception as e:
            await context.bot.send_message(chat_id, f"Exception: {str(e)}")
    else:
        await context.bot.send_message(chat_id, "Send a valid YouTube link.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
