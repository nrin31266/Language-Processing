import httpx
import json
import os

async def fetch_json_from_url(url: str):
    """Download JSON từ URL và trả về dict."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"⚠️ Không tải được metadata từ {url}: {e}")
        return None

def file_exists(path: str) -> bool:
    """
    Kiểm tra file local có tồn tại trong hệ thống hay không.
    :param path: đường dẫn file, vd: 'src/temp/audio_files/file.mp3'
    :return: True nếu tồn tại, False nếu không
    """
    return os.path.isfile(path)