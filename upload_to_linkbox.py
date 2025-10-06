import os
import sys
import json
import hashlib
import requests
import subprocess
import tempfile

LINKBOX_API_TOKEN = os.environ["LINKBOX_API_TOKEN"]
LINKBOX_FOLDER_ID = os.environ.get("LINKBOX_FOLDER_ID", "0")

def md5_of_first_10mb(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        chunk = f.read(10 * 1024 * 1024)  # first 10 MB
        hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_upload_url(file_md5, file_size):
    url = "https://www.linkbox.to/api/open/get_upload_url"
    params = {
        "fileMd5ofPre10m": file_md5,
        "fileSize": file_size,
        "token": LINKBOX_API_TOKEN
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    return data["data"]["signUrl"]

def create_file_item(file_md5, file_size, file_name):
    url = "https://www.linkbox.to/api/open/folder_upload_file"
    params = {
        "fileMd5ofPre10m": file_md5,
        "fileSize": file_size,
        "pid": LINKBOX_FOLDER_ID,
        "diyName": file_name,
        "token": LINKBOX_API_TOKEN
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if data["status"] != 1:
        raise Exception(f"Upload item creation failed: {data}")
    return data["data"]["itemId"]

def upload_file_to_linkbox(file_path):
    file_size = os.path.getsize(file_path)
    file_md5 = md5_of_first_10mb(file_path)
    file_name = os.path.basename(file_path)

    # Step 1: get upload URL
    sign_url = get_upload_url(file_md5, file_size)

    # Step 2: upload file
    with open(file_path, "rb") as f:
        r = requests.put(sign_url, data=f)
        r.raise_for_status()

    # Step 3: create file item in LinkBox
    item_id = create_file_item(file_md5, file_size, file_name)
    return f"https://www.linkbox.to/file/{item_id}"

def download_youtube_video(url):
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "%(title)s.%(ext)s")
    subprocess.run([
        "yt-dlp", "-f", "best", "-o", output_path, url
    ], check=True)
    # Return path of downloaded file
    files = os.listdir(tmp_dir)
    if not files:
        raise Exception("Download failed: no files found")
    return os.path.join(tmp_dir, files[0])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_to_linkbox.py <youtube_url>")
        sys.exit(1)

    youtube_url = sys.argv[1]
    try:
        print("Downloading video...")
        file_path = download_youtube_video(youtube_url)
        print(f"Uploading {file_path} to LinkBox...")
        link = upload_file_to_linkbox(file_path)
        print(f"✅ Success! Link: {link}")
    except Exception as e:
        print(f"❌ Error: {e}")
