import cloudinary.uploader
from src.errors.base_exception import BaseException
from src.errors.base_error_code import BaseErrorCode
import logging
from typing import Union, IO

logger = logging.getLogger(__name__)

def upload_file(
    file_source: Union[str, IO], 
    public_id: str, # duong dan, ten file tren cloudinary. Example: "folder/subfolder/filename"
    resource_type: str = "auto"
) -> str:
    """
    Upload một file lên Cloudinary và trả về secure URL.
    :param file_source: Đường dẫn file (str) hoặc file object (IO)
    :param public_id: Tên file trên Cloudinary
    :param resource_type: "auto", "image", "video" (audio được coi như video)
    :return: URL file đã upload
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
        secure_url = upload_result.get('secure_url')
        if not secure_url:
            raise Exception("Upload thành công nhưng không nhận được secure_url.")
        
        logger.info(f"Upload thành công. URL: {secure_url}")
        return secure_url
        
    except Exception as e:
        logger.error(f"Cloudinary upload thất bại cho {public_id}: {e}", exc_info=True)
        raise BaseException(
            BaseErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Lỗi khi upload file lên cloud: {str(e)}"
        )
def upload_json_content(json_str: str, public_id: str) -> str:
    """
    Upload nội dung JSON trực tiếp lên Cloudinary.
    :param json_str: nội dung JSON dạng string
    :param public_id: tên file trên Cloudinary (không cần .json)
    :return: secure_url của file JSON trên Cloudinary
    """
    try:
        logger.info(f"Uploading JSON content as {public_id}.json...")

        # Upload dạng raw file (Cloudinary sẽ lưu như một file binary)
        upload_result = cloudinary.uploader.upload(
            json_str.encode("utf-8"),      # chuyển string → bytes
            public_id=public_id,
            resource_type="raw",           # dùng raw thay vì image/video
            format="json",                 # ép Cloudinary lưu dạng JSON
            overwrite=True
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
            message=f"Lỗi khi upload JSON lên Cloudinary: {str(e)}"
        )