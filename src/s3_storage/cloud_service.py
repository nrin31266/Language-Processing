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
