import httpx
import json
import os
import json
from typing import Any, Dict, Optional
from pydantic import ValidationError
from src.dto import AiMetadataDto


def lessonParseAiMetaData(metadata: Optional[Any]) -> AiMetadataDto:
    """
    Parse metadata (string JSON hoặc dict) thành AiMetadataDto.
    Trả về DTO rỗng nếu metadata null hoặc lỗi format.
    """

    if not metadata:
        return AiMetadataDto()  # metadata rỗng

    # 1. Nếu là string → parse JSON
    if isinstance(metadata, str):
        try:
            data = json.loads(metadata)
        except Exception:
            # JSON lỗi → trả rỗng
            return AiMetadataDto()
    # 2. Nếu là dict → dùng luôn
    elif isinstance(metadata, dict):
        data = metadata
    else:
        return AiMetadataDto()

    # Chuẩn hóa key: camelCase → snake_case
    normalized = {}
    for key, value in data.items():
        snake = (
            key.replace("-", "_")
                .replace(" ", "_")
                .replace("Started", "_started")
                .lower()
        )
        normalized[snake] = value

    # Parse DTO
    try:
        return AiMetadataDto(**normalized)
    except ValidationError:
        return AiMetadataDto()

async def fetch_json_from_url(url: str):
    """Download JSON từ URL và trả về dict."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Lỗi khi tải JSON từ {url}: {e}")
        return None

def file_exists(path: str) -> bool:
    """
    Kiểm tra file local có tồn tại trong hệ thống hay không.
    :param path: đường dẫn file, vd: 'src/temp/audio_files/file.mp3'
    :return: True nếu tồn tại, False nếu không
    """
    return os.path.isfile(path)
def remove_local_file(file_path: str):
    try:
        os.remove(file_path)
        print(f"Đã xóa file tạm thời: {file_path}")
    except OSError as e:
        print(f"Lỗi khi xóa file {file_path}: {e.strerror}")