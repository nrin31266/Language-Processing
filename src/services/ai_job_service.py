from src import dto
from src.errors.base_exception import BaseException
from src.errors.base_error_code import BaseErrorCode
from src.s3_storage  import cloud_service
import yt_dlp
import os
from datetime import datetime
import logging as logger

# --- Import mới cho download_audio_file ---
import requests
import uuid  # Để tạo tên file an toàn
import mimetypes # Để đoán đuôi file
from urllib.parse import urlparse # Để lấy tên file gốc từ URL
from src.redis import redis_service


async def aiJobWasCancelled(ai_job_id: str) -> bool:
    """Kiểm tra xem AI Job có bị hủy không."""
    status = await redis_service.redis_get(f"aiJobStatus:{ai_job_id}")
    print(f"🔍 Kiểm tra trạng thái AI Job {ai_job_id}: {status}")
    if not status:
        return False  # Chưa có gì → chưa bị hủy

    return status.strip('"') == "CANCELLED"


