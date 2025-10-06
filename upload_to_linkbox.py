import os
import subprocess
import tempfile
import shutil

LINKBOX_API_TOKEN = os.getenv("LINKBOX_API_TOKEN")
LINKBOX_FOLDER_ID = os.getenv("LINKBOX_FOLDER_ID")

if not LINKBOX_API_TOKEN or not LINKBOX_FOLDER_ID:
    raise ValueError("LINKBOX_API_TOKEN and LINKBOX_FOLDER_ID must be set in environment variables!")

async def upload_file_to_linkbox(youtube_url, update=None, context=None):
    """
    Download a YouTube video using yt-dlp and upload it to Linkbox.
    Returns the public URL of the uploaded file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Download YouTube video
            cmd = [
                "yt-dlp",
                "-f", "best",
                "-o", os.path.join(tmpdir, "%(title)s.%(ext)s"),
                youtube_url
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                raise RuntimeError(process.stderr)

            # Find the downloaded file
            files = os.listdir(tmpdir)
            if not files:
                raise RuntimeError("No file was downloaded.")
            file_path = os.path.join(tmpdir, files[0])

            # Upload to Linkbox
            # This is a placeholder: replace with actual API call
            # Example: use requests.post() to upload file
            # For demonstration, we'll just return a fake URL
            linkbox_url = f"https://linkbox.to/fake/{os.path.basename(file_path)}"

            return linkbox_url

        except Exception as e:
            raise e
