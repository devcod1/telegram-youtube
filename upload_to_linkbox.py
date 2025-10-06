import requests
import hashlib
import os
import sys
from yt_dlp import YoutubeDL

LINKBOX_TOKEN = os.environ['LINKBOX_API_TOKEN']
UPLOAD_FOLDER_ID = int(os.environ.get('LINKBOX_FOLDER_ID', 0))

def md5_first_10mb(file_path):
    with open(file_path, 'rb') as f:
        data = f.read(10 * 1024 * 1024)  # first 10MB
    return hashlib.md5(data).hexdigest()

def get_upload_url(file_md5, file_size):
    url = "https://www.linkbox.to/api/open/get_upload_url"
    params = {
        "fileMd5ofPre10m": file_md5,
        "fileSize": file_size,
        "token": LINKBOX_TOKEN
    }
    r = requests.get(url, params=params).json()
    if r["status"] != 1:
        raise Exception(r)
    return r["data"]["signUrl"]

def upload_file(file_path, sign_url):
    with open(file_path, 'rb') as f:
        r = requests.put(sign_url, data=f)
    if r.status_code not in [200, 201]:
        raise Exception("Upload failed")

def create_file_item(file_md5, file_size, file_name):
    url = "https://www.linkbox.to/api/open/folder_upload_file"
    params = {
        "fileMd5ofPre10m": file_md5,
        "fileSize": file_size,
        "pid": UPLOAD_FOLDER_ID,
        "diyName": file_name,
        "token": LINKBOX_TOKEN
    }
    r = requests.get(url, params=params).json()
    if r["status"] != 1:
        raise Exception(r)
    return r["data"]["itemId"]

def share_file(item_id):
    url = "https://www.linkbox.to/api/open/file_share"
    params = {
        "itemIds": item_id,
        "expire_enum": 4,  # permanent
        "token": LINKBOX_TOKEN
    }
    r = requests.get(url, params=params).json()
    if r["status"] != 1:
        raise Exception(r)
    return r["data"]["shareToken"]

def download_youtube(url):
    ydl_opts = {"outtmpl": "video.%(ext)s", "format": "best"}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)
        filename = ydl.prepare_filename(info)
    return filename

if __name__ == "__main__":
    youtube_url = sys.argv[1]  # pass YouTube link
    file_name = download_youtube(youtube_url)
    file_size = os.path.getsize(file_name)
    file_md5 = md5_first_10mb(file_name)
    sign_url = get_upload_url(file_md5, file_size)
    upload_file(file_name, sign_url)
    item_id = create_file_item(file_md5, file_size, os.path.basename(file_name))
    share_token = share_file(item_id)
    print("LinkBox Share Link:", f"https://www.linkbox.to/s/{share_token}")
