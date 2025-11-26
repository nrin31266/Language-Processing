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
