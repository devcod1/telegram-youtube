# upload_to_linkbox.py
import os
import sys
import hashlib
import asyncio
import tempfile
import subprocess
import shutil
import aiohttp

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
    item_id = data["data"].get("itemId")
    if not item_id:
        raise RuntimeError(f"folder_upload_file did not return itemId: {data}")
    return item_id

async def share_file(session: aiohttp.ClientSession, item_id: str) -> str:
    url = "https://www.linkbox.to/api/open/file_share"
    params = {"itemIds": item_id, "expire_enum": 4, "token": LINKBOX_API_TOKEN}
    async with session.get(url, params=params, timeout=60) as r:
        data = await r.json()
    if data.get("status") != 1:
        raise RuntimeError(f"file_share failed: {data}")
    token = data["data"].get("shareToken")
    if not token:
        raise RuntimeError(f"file_share did not return shareToken: {data}")
    return token

async def upload_file_via_signed_url(session: aiohttp.ClientSession, sign_url: str, file_path: str) -> None:
    file_size = os.path.getsize(file_path)
    headers = {"Content-Length": str(file_size)}
    # stream file via blocking file object (aiohttp will handle streaming)
    async with session.put(sign_url, data=open(file_path, "rb"), headers=headers, timeout=3600) as r:
        if r.status not in (200, 201):
            text = await r.text()
            raise RuntimeError(f"PUT to signUrl failed: status={r.status} text={text}")

async def run_yt_dlp_no_cookies(youtube_url: str, tmpdir: str) -> str:
    out_template = os.path.join(tmpdir, "%(title)s.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "-f", "best", "-o", out_template, youtube_url]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, text=True)
    stdout, stderr = await proc.communicate()
    combined = (stdout or "") + "\n" + (stderr or "")
    low = combined.lower()
    if "sign in to confirm" in low or "use --cookies" in low or "authentication" in low:
        raise RuntimeError("This video requires a signed-in session (YouTube is blocking anonymous downloads). I can't download it without cookies/authentication.")
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed (rc={proc.returncode}): {stderr.strip() or stdout.strip()}")
    # find downloaded file
    files = [f for f in os.listdir(tmpdir) if not f.startswith(".")]
    if not files:
        raise RuntimeError("yt-dlp finished but no file found in tmpdir")
    files_full = [os.path.join(tmpdir, f) for f in files]
    files_full.sort(key=lambda p: os.path.getsize(p), reverse=True)
    return files_full[0]

async def upload_file_to_linkbox(youtube_url: str) -> str:
    tmpdir = tempfile.mkdtemp(prefix="yt_")
    try:
        video_path = await run_yt_dlp_no_cookies(youtube_url, tmpdir)

        file_md5 = md5_first_10mb(video_path)
        file_size = os.path.getsize(video_path)
        file_name = os.path.basename(video_path)

        async with aiohttp.ClientSession() as session:
            sign_url = await get_upload_url(session, file_md5, file_size)
            await upload_file_via_signed_url(session, sign_url, video_path)
            item_id = await create_file_item(session, file_md5, file_size, file_name)
            share_token = await share_file(session, item_id)

        # final link
        final = f"https://www.linkbox.to/s/{share_token}"
        return final

    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

# CLI
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
