from __future__ import annotations # Set in top of file for forward type references
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
# src/utils/text_utils.py



import re
import unicodedata
from typing import Optional

# Các punctuation phổ biến trong tiếng Anh (giống bên Java)
_PUNCTS = '.,!?;:"()[]{}…—–-'


def has_punctuation(token: Optional[str]) -> bool:
    """
    Tương đương Java:
      public boolean hasPunctuation(String token)

    Trả về True nếu trong token có bất kỳ ký tự punctuation trong _PUNCTS.
    """
    if not token:  # None hoặc rỗng
        return False

    return any(ch in _PUNCTS for ch in token)


def normalize_word_lower(token: Optional[str]) -> Optional[str]:
    """
    Tương đương Java:
      public String normalizeWordLower(String token)

    - lower-case
    - bỏ dấu '
    - chỉ giữ [a-z0-9]
    """
    if token is None:
        return None

    s = token.lower().replace("'", "")  # it's -> its
    # ❗ giữ lại chữ + số
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def to_slug(value: Optional[str]) -> Optional[str]:
    """
    Tương đương Java:
      public String toSlug(String input)

    - Bỏ dấu tiếng Việt (normalize unicode NFD + remove combining marks)
    - Chỉ giữ a-z, 0-9, space, '-'
    - Space -> '-'
    - Gom nhiều '-' liên tiếp thành 1
    """
    if value is None:
        return None

    # 1) Normalize unicode (loại dấu tiếng Việt)
    normalized = unicodedata.normalize("NFD", value)
    # Bỏ các ký tự dấu (combining diacritical marks)
    without_accents = "".join(
        ch for ch in normalized
        if unicodedata.category(ch) != "Mn"  # Mn = Mark, Nonspacing
    )

    # 2) Chỉ giữ a-z, 0-9, space và '-'
    cleaned = re.sub(r"[^a-z0-9\s-]", "", without_accents.lower())

    # 3) Replace space thành dấu '-'
    dashed = re.sub(r"\s+", "-", cleaned.strip())

    # 4) Remove multiple hyphens
    slug = re.sub(r"-{2,}", "-", dashed)

    return slug
