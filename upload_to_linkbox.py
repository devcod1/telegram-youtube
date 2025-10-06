import sys
import os
import hashlib
import requests
import subprocess

# Check YouTube link argument
if len(sys.argv) < 2:
    print("Error: No YouTube link provided")
    sys.exit(1)

youtube_url = sys.argv[1]

LINKBOX_API_TOKEN = os.environ["LINKBOX_API_TOKEN"]
UPLOAD_FOLDER_ID = os.environ.get("LINKBOX_FOLDER_ID", "0")

# Download video using yt-dlp
filename = "video.mp4"
try:
    subprocess.run(["yt-dlp", "-o", filename, youtube_url], check=True)
except Exception as e:
    print(f"Error downloading video: {str(e)}")
    sys.exit(1)

# MD5 of first 10 MB
def md5_first_10mb(file_path):
    m = hashlib.md5()
    with open(file_path, "rb") as f:
        data = f.read(10 * 1024 * 1024)
        m.update(data)
    return m.hexdigest()

file_md5 = md5_first_10mb(filename)
file_size = os.path.getsize(filename)

# Get upload URL
resp = requests.get(
    "https://www.linkbox.to/api/open/get_upload_url",
    params={
        "fileMd5ofPre10m": file_md5,
        "fileSize": file_size,
        "token": LINKBOX_API_TOKEN
    }
).json()

if resp["status"] != 1:
    print("Error getting upload URL:", resp)
    sys.exit(1)

sign_url = resp["data"]["signUrl"]

# Upload file
with open(filename, "rb") as f:
    put_resp = requests.put(sign_url, data=f)

if put_resp.status_code not in [200, 201]:
    print("Upload failed")
    sys.exit(1)

# Create file item in LinkBox
resp2 = requests.get(
    "https://www.linkbox.to/api/open/folder_upload_file",
    params={
        "fileMd5ofPre10m": file_md5,
        "fileSize": file_size,
        "pid": UPLOAD_FOLDER_ID,
        "diyName": filename,
        "token": LINKBOX_API_TOKEN
    }
).json()

if resp2["status"] != 1:
    print("Error creating file item:", resp2)
    sys.exit(1)

item_id = resp2["data"]["itemId"]

# Share file
resp3 = requests.get(
    "https://www.linkbox.to/api/open/file_share",
    params={
        "itemIds": item_id,
        "expire_enum": 4,
        "token": LINKBOX_API_TOKEN
    }
).json()

if resp3["status"] != 1:
    print("Error sharing file:", resp3)
    sys.exit(1)

share_link = resp3["data"]["shareToken"]
print(f"Uploaded successfully! Link: https://www.linkbox.to/s/{share_link}")
