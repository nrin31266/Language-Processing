import asyncio
import logging
from typing import Union, IO

import cloudinary.uploader

from src.errors.base_exception import BaseException
from src.errors.base_error_code import BaseErrorCode

logger = logging.getLogger(__name__)


# =========================
#  SYNC IMPLEMENTATION
# =========================

def _upload_file_sync(
    file_source: Union[str, IO],
    public_id: str,  # đường dẫn, tên file trên cloudinary. Example: "folder/subfolder/filename"
    resource_type: str = "auto",
) -> str:
    """
    Sync: Upload một file lên Cloudinary và trả về secure URL.
    Dùng nội bộ, bọc bởi hàm async upload_file().
    """
    action = "Uploading file"
    if isinstance(file_source, str):
        action = f"Uploading local file: {file_source}"

    logger.info(f"{action} to Cloudinary as {public_id}...")

    try:
        upload_result = cloudinary.uploader.upload(
            file_source,
            resource_type=resource_type,
            public_id=public_id,
            overwrite=True,
        )
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise Exception("Upload thành công nhưng không nhận được secure_url.")

        logger.info(f"Upload thành công. URL: {secure_url}")
        return secure_url

    except Exception as e:
        logger.error(
            f"Cloudinary upload thất bại cho {public_id}: {e}",
            exc_info=True,
        )
        raise BaseException(
            BaseErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Lỗi khi upload file lên cloud: {str(e)}",
        )


def _upload_json_content_sync(json_str: str, public_id: str) -> str:
    """
    Sync: Upload nội dung JSON trực tiếp lên Cloudinary.
    Dùng nội bộ, bọc bởi hàm async upload_json_content().
    """
    try:
        logger.info(f"Uploading JSON content as {public_id}.json...")

        # Upload dạng raw file (Cloudinary sẽ lưu như một file binary)
        upload_result = cloudinary.uploader.upload(
            json_str.encode("utf-8"),  # chuyển string → bytes
            public_id=public_id,
            resource_type="raw",       # dùng raw thay vì image/video
            format="json",             # ép Cloudinary lưu dạng JSON
            overwrite=True,
        )

        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise Exception("Upload JSON thành công nhưng không nhận secure_url.")

        logger.info(f"Upload JSON thành công: {secure_url}")
        return secure_url

    except Exception as e:
        logger.error(f"Upload JSON failed for {public_id}: {e}", exc_info=True)
        raise BaseException(
            BaseErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Lỗi khi upload JSON lên Cloudinary: {str(e)}",
        )


# =========================
#  ASYNC WRAPPERS
# =========================

async def upload_file(
    file_source: Union[str, IO],
    public_id: str,
    resource_type: str = "auto",
) -> str:
    """
    Async: Upload file lên Cloudinary ở thread pool, KHÔNG block event loop.

    Ví dụ dùng:
        url = await cloud_service.upload_file(path, public_id="lps/lessons/audio/123", resource_type="video")
    """
    return await asyncio.to_thread(
        _upload_file_sync,
        file_source,
        public_id,
        resource_type,
    )


async def upload_json_content(json_str: str, public_id: str) -> str:
    """
    Async: Upload JSON lên Cloudinary ở thread pool, KHÔNG block event loop.

    Ví dụ dùng:
        url = await cloud_service.upload_json_content(json.dumps(data), public_id="lps/lessons/1/ai-metadata")
    """
    return await asyncio.to_thread(
        _upload_json_content_sync,
        json_str,
        public_id,
    )
