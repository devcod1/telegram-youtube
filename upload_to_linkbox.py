# upload_to_linkbox.py
import os
import sys
import hashlib
import asyncio
import tempfile
import subprocess
import shutil
from typing import Optional

import aiohttp

# LinkBox env
LINKBOX_API_TOKEN = os.getenv("LINKBOX_API_TOKEN")
LINKBOX_FOLDER_ID = os.getenv("LINKBOX_FOLDER_ID", "0")

if not LINKBOX_API_TOKEN:
    raise ValueError("LINKBOX_API_TOKEN must be set in environment variables!")

def md5_first_10mb(path: str) -> str:
    m = hashlib.md5()
    with open(path, "rb") as f:
        chunk = f.read(10 * 1024 * 1024)
        m.update(chunk)
    return m.hexdigest()

async def get_upload_url(session: aiohttp.ClientSession, file_md5: str, file_size: int) -> str:
    url = "https://www.linkbox.to/api/open/get_upload_url"
    params = {"fileMd5ofPre10m": file_md5, "fileSize": file_size, "token": LINKBOX_API_TOKEN}
    async with session.get(url, params=params, timeout=60) as r:
        data = await r.json()
    if data.get("status") != 1:
        raise RuntimeError(f"get_upload_url failed: {data}")
    return data["data"]["signUrl"]

async def create_file_item(session: aiohttp.ClientSession, file_md5: str, file_size: int, file_name: str) -> str:
    url = "https://www.linkbox.to/api/open/folder_upload_file"
    params = {"fileMd5ofPre10m": file_md5, "fileSize": file_size, "pid": LINKBOX_FOLDER_ID, "diyName": file_name, "token": LINKBOX_API_TOKEN}
    async with session.get(url, params=params, timeout=60) as r:
        data = await r.json()
    if data.get("status") != 1:
        raise RuntimeError(f"folder_upload_file failed: {data}")
    return data["data"].get("itemId")

async def share_file(session: aiohttp.ClientSession, item_id: str) -> str:
    url = "https://www.linkbox.to/api/open/file_share"
    params = {"itemIds": item_id, "expire_enum": 4, "token": LINKBOX_API_TOKEN}
    async with session.get(url, params=params, timeout=60) as r:
        data = await r.json()
    if data.get("status") != 1:
        raise RuntimeError(f"file_share failed: {data}")
    return data["data"].get("shareToken")

async def upload_file_via_signed_url(session: aiohttp.ClientSession, sign_url: str, file_path: str) -> None:
    file_size = os.path.getsize(file_path)
    headers = {"Content-Length": str(file_size)}
    # Use streaming upload
    async with session.put(sign_url, data=open(file_path, "rb"), headers=headers, timeout=3600) as r:
        if r.status not in (200, 201):
            text = await r.text()
            raise RuntimeError(f"PUT to signUrl failed: status={r.status} text={text}")

async def run_yt_dlp_no_cookies(youtube_url: str, tmpdir: str) -> str:
    """
    Download a single video with yt-dlp without cookies (no playlist).
    Returns path to downloaded file or raises RuntimeError with clear message.
    """
    out_template = os.path.join(tmpdir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",          # important: don't download playlists
        "-o", out_template,
        youtube_url
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, text=True)
    stdout, stderr = await proc.communicate()
    combined = (stdout or "") + "\n" + (stderr or "")

    # Detect common auth-required message from yt-dlp / youtube
    if "Sign in to confirm" in combined or "sign in to" in combined.lower() or "use --cookies" in combined.lower() or "authentication" in combined.lower():
        # Return a clear, user-friendly error
        raise RuntimeError("This video requires a signed-in session (YouTube is blocking anonymous downloads). I can't download it without cookies/authentication.")
    if proc.returncode != 0:
        # Other failure
        raise RuntimeError(f"yt-dlp failed (rc={proc.returncode}): {stderr.strip() or stdout.strip()}")
    # find downloaded file
    files = [f for f in os.listdir(tmpdir) if not f.startswith(".")]
    if not files:
        raise RuntimeError("yt-dlp finished but no file found")
    files_full = [os.path.join(tmpdir, f) for f in files]
    files_full.sort(key=lambda p: os.path.getsize(p), reverse=True)
    return files_full[0]

async def upload_file_to_linkbox(youtube_url: str) -> str:
    """
    Main entry: try cookie-free download; if success upload to LinkBox and return share URL.
    If video requires login, raises RuntimeError with a clear message.
    """
    tmpdir = tempfile.mkdtemp(prefix="yt_")
    try:
        # 1) Attempt cookie-free download
        video_path = await run_yt_dlp_no_cookies(youtube_url, tmpdir)

        # 2) Prepare upload
        file_md5 = md5_first_10mb(video_path)
        file_size = os.path.getsize(video_path)
        file_name = os.path.basename(video_path)

        async with aiohttp.ClientSession() as session:
            sign_url = await get_upload_url(session, file_md5, file_size)
            await upload_file_via_signed_url(session, sign_url, video_path)
            item_id = await create_file_item(session, file_md5, file_size, file_name)
            share_token = await share_file(session, item_id)

        return f"https://www.linkbox.to/s/{share_token}"

    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

# CLI support
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_to_linkbox.py <youtube_url>")
        sys.exit(1)
    url = sys.argv[1]
    try:
        link = asyncio.run(upload_file_to_linkbox(url))
        print(link)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
