import os
import asyncio
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from upload_to_linkbox import upload_file_to_linkbox
import subprocess

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if "youtube.com/watch" in text or "youtu.be/" in text:
        status_msg = await context.bot.send_message(chat_id, "Received YouTube link. Downloading...")

        # Use temporary directory to store downloaded video
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "%(title)s.%(ext)s")
            cmd = [
                "yt-dlp",
                "--no-playlist",      # only single video
                "-f", "best",
                "-o", video_path,
                text
            ]
            try:
                # Run yt-dlp and capture output
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )

                # Print progress to console and update Telegram message
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_text = line.decode().strip()
                    print(line_text)
                    try:
                        await status_msg.edit_text(f"Downloading...\n{line_text}")
                    except:
                        # Ignore "Message not modified" errors
                        pass

                returncode = await process.wait()
                if returncode != 0:
                    await context.bot.send_message(chat_id, f"❌ Download failed (yt-dlp returned {returncode})")
                    return

                # Find the downloaded file
                downloaded_files = os.listdir(tmpdir)
                if not downloaded_files:
                    await context.bot.send_message(chat_id, "❌ No video file found after download.")
                    return
                file_to_upload = os.path.join(tmpdir, downloaded_files[0])

                # Upload to Linkbox
                await status_msg.edit_text("Uploading to Linkbox...")
                link = await upload_file_to_linkbox(file_to_upload)
                await context.bot.send_message(chat_id, f"✅ Uploaded successfully!\n{link}")

            except Exception as e:
                await context.bot.send_message(chat_id, f"❌ Exception: {str(e)}")


async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
