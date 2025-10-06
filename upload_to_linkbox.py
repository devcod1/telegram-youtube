import os
import aiohttp

LINKBOX_API_TOKEN = os.environ.get("LINKBOX_API_TOKEN")
LINKBOX_FOLDER_ID = os.environ.get("LINKBOX_FOLDER_ID")

async def upload_file_to_linkbox(file_path: str) -> str:
    """Uploads a file to Linkbox and returns the public link."""
    filename = os.path.basename(file_path)
    url = "https://api.linkbox.to/upload"

    headers = {
        "Authorization": f"Bearer {LINKBOX_API_TOKEN}"
    }

    data = aiohttp.FormData()
    data.add_field("folder_id", LINKBOX_FOLDER_ID)
    data.add_field("file", open(file_path, "rb"), filename=filename)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Linkbox upload failed: {resp.status} {text}")
            result = await resp.json()
            return result.get("link")  # adjust depending on Linkbox API response
