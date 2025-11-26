
from src import dto
from src.errors.base_exception import BaseException
from src.errors.base_error_code import BaseErrorCode
from src.s3_storage  import cloud_service
import yt_dlp
import os
from datetime import datetime
import logging as logger
import uuid
# --- Import mới cho download_audio_file ---
import requests
import uuid  # Để tạo tên file an toàn
import mimetypes # Để đoán đuôi file
from urllib.parse import urlparse # Để lấy tên file gốc từ URL

# ==========================================================
# PHẦN LẤY THÔNG TIN (INFO EXTRACTOR)
# ==========================================================
YDL_INFO_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'extract_flat': 'in_playlist',
}
ydl_info_extractor = yt_dlp.YoutubeDL(YDL_INFO_OPTS)


# ==========================================================
# PHẦN TẢI VỀ (DOWNLOADER)
# ==========================================================

# 1. ĐỊNH NGHĨA NƠI LƯU FILE (QUAN TRỌNG)
# Đây là nơi file MP3 sẽ được lưu.
# Hãy thay bằng đường dẫn tuyệt đối trên server của bạn.
# Ví dụ: '/var/www/my-app/media/' hoặc đọc từ biến môi trường
AUDIO_SAVE_PATH = os.getenv('AUDIO_SAVE_PATH', 'src/temp/audio_files')

# Tạo thư mục này nếu nó chưa tồn tại
os.makedirs(AUDIO_SAVE_PATH, exist_ok=True)


# 2. CẤU HÌNH ĐỂ TẢI MP3
YDL_DOWNLOAD_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'format': 'bestaudio/best', # Chỉ tải âm thanh tốt nhất
    
    # Đây là câu trả lời cho "lưu vào đâu":
    # '%(id)s' sẽ được thay bằng ID của video (ví dụ: dQw4w9WgXcQ)
    # '%(ext)s' sẽ là 'mp3' (do postprocessor bên dưới)
    'outtmpl': f'{AUDIO_SAVE_PATH}/%(id)s.%(ext)s',
    
    # Cấu hình chuyển đổi sang MP3 (Yêu cầu FFmpeg)
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192', # Chất lượng 192kbps
    }],
}

# 3. TẠO ĐỐI TƯỢNG DOWNLOADER TOÀN CỤC
ydl_downloader = yt_dlp.YoutubeDL(YDL_DOWNLOAD_OPTS)



# ==========================================================
# CẤU HÌNH UPLOAD VÀ GIỚI HẠN
# ==========================================================
# Thư mục cơ sở trên Cloudinary
CLOUDINARY_BASE_FOLDER = "fastapi/test1/audio_files" 
# Giới hạn kích thước file tải về từ URL (ví dụ: 50MB)
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024 # 50MB

def download_youtube_audio(rq: dto.MediaAudioCreateRequest) -> dto.AudioInfo:
    print("Đang lấy thông tin video...")
    
    try:
        # ==========================================================
        # PHẦN 1: LẤY THÔNG TIN
        # ==========================================================
        info = ydl_info_extractor.extract_info(rq.input_url, download=False)
        
        print("\n--- Thông tin Video ---")
        print(f"Tiêu đề: {info['title']}")
        print(f"Thời lượng: {info['duration_string']}")

        # Kiểm tra thời lượng 
        duration_sec = info.get('duration', 0)
        if duration_sec > 600: # Lớn hơn 10 phút (600 giây)
            raise BaseException(BaseErrorCode.BAD_REQUEST, 
                                message=f"Video quá dài ({duration_sec}s). Chỉ chấp nhận video dưới 10 phút.")

        # ==========================================================
        # PHẦN 2: TẢI FILE MP3
        # ==========================================================
        print(f"Video hợp lệ (Thời lượng: {duration_sec}s). Bắt đầu tải...")

        # Gọi download bằng đối tượng downloader toàn cục
        # Tác vụ này sẽ block cho đến khi tải và convert xong
        ydl_downloader.download([rq.input_url])

        # Xây dựng đường dẫn file cuối cùng (để lưu vào DB)
        video_id = info.get('id')
        thumbnailUrl = info.get('thumbnail')
        print(f"Thumbnail URL: {thumbnailUrl}")
        final_mp3_path = f"{AUDIO_SAVE_PATH}/{video_id}.mp3"
        
        print(f"Đã tải và convert thành công: {final_mp3_path}")
        
        return dto.AudioInfo(
            file_path=final_mp3_path,
            duration=duration_sec,
            sourceReferenceId=video_id,
            thumbnailUrl=thumbnailUrl
        )

    except yt_dlp.utils.DownloadError as e:
        raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"Lỗi khi xử lý video: {str(e)}")
    except Exception as e:
        raise BaseException(BaseErrorCode.INTERNAL_SERVER_ERROR, message=f"Lỗi hệ thống: {str(e)}")

def download_audio_file(rq: dto.MediaAudioCreateRequest) -> dto.AudioInfo:
    """
    Tải file audio từ một URL bất kỳ (phiên bản an toàn).
    """
    audio_url = rq.input_url
    logger.info(f"Bắt đầu xử lý file audio từ URL: {audio_url}")
    try:
        # --- BƯỚC 1: KIỂM TRA HEADERS (VALIDATION) ---
        # Gửi HEAD request để kiểm tra trước khi tải
        # timeout=5: Chờ tối đa 5 giây
        # allow_redirects=True: Cho phép theo dõi chuyển hướng (vd: http -> https)
        # with để tự động đóng kết nối sau khi xong
        with requests.head(audio_url, allow_redirects=True, timeout=5) as head_resp:
            head_resp.raise_for_status()  # Ném lỗi nếu status không phải 2xx
            
            # 1.1. Kiểm tra loại file (Content-Type)
            content_type = head_resp.headers.get('Content-Type', '').lower()
            if not content_type.startswith('audio/'):
                logger.warning(f"URL bị từ chối: Content-Type không phải audio ({content_type})")
                raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"URL không trỏ đến file audio (phát hiện: {content_type})")
            
            # 1.2. Kiểm tra dung lượng (Content-Length)
            content_length = head_resp.headers.get('Content-Length')
            if content_length and int(content_length) > MAX_AUDIO_SIZE_BYTES:
                file_size_mb = int(content_length) / 1024 / 1024
                limit_mb = MAX_AUDIO_SIZE_BYTES / 1024 / 1024
                logger.warning(f"URL bị từ chối: File quá lớn ({file_size_mb:.2f} MB)")
                raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"File audio quá lớn ({file_size_mb:.2f} MB). Giới hạn: {limit_mb} MB")
            # --- BƯỚC 2: TẠO TÊN FILE AN TOÀN ---
            # Lấy đuôi file từ content-type (ví dụ: 'audio/mpeg' -> '.mp3')
            ext = mimetypes.guess_extension(content_type) or '.dat' # Fallback nếu không đoán được
            # Tạo tên file duy nhất bằng UUID để tránh trùng lặp
            filename = f"{rq.audio_name}{ext}" if rq.audio_name else f"{uuid.uuid4()}{ext}"
            save_path = os.path.join(AUDIO_SAVE_PATH, filename)
            
        # --- BƯỚC 3: TẢI FILE (STREAM) ---
        logger.info(f"Đang tải file về {save_path}...")
        # timeout=60: Cho phép tối đa 60 giây để tải
        with requests.get(audio_url, stream=True, timeout=60) as r_download:
            r_download.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r_download.iter_content(chunk_size=8192): # Tải từng cục 8KB
                    if chunk:
                        f.write(chunk)
            
        
        logger.info(f"Đã tải file audio thành công: {save_path}")
        return dto.AudioInfo(
            file_path=save_path,
            sourceReferenceId=filename,
        )
    except requests.exceptions.Timeout:
        logger.error(f"Lỗi Timeout khi tải file: {audio_url}")
        raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"Tải file thất bại: Hết thời gian chờ (Timeout)")
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi khi tải file audio từ URL: {e}")
        raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"Lỗi tải file audio từ URL: {str(e)}")
    except BaseException: # Ném lại lỗi BaseException (ví dụ: file quá lớn)
        raise
    except Exception as e:
        logger.error(f"Lỗi không xác định khi tải file: {e}", exc_info=True)
        raise BaseException(BaseErrorCode.INTERNAL_SERVER_ERROR, message=f"Lỗi hệ thống khi xử lý file: {str(e)}")



# def upload_audio_file(file_path: str, public_id: str):
#     return cloud_service.upload_file(file_path, public_id, resource_type="video")  # audio được coi như video

def remove_local_file(file_path: str):
    try:
        os.remove(file_path)
        print(f"Đã xóa file tạm thời: {file_path}")
    except OSError as e:
        print(f"Lỗi khi xóa file {file_path}: {e.strerror}")

# ==========================================================
# from sqlalchemy.orm import Session
# from src import dto, models
# from src.errors.base_exception import BaseException
# from src.errors.base_error_code import BaseErrorCode
# from src.cloud  import cloud_service
# import yt_dlp
# import os
# from datetime import datetime
# import logging as logger

# # --- Import mới cho download_audio_file ---
# import requests
# import uuid  # Để tạo tên file an toàn
# import mimetypes # Để đoán đuôi file
# from urllib.parse import urlparse # Để lấy tên file gốc từ URL

# # ==========================================================
# # PHẦN LẤY THÔNG TIN (INFO EXTRACTOR)
# # ==========================================================
# YDL_INFO_OPTS = {
#     'quiet': True,
#     'no_warnings': True,
#     'noplaylist': True,
#     'extract_flat': 'in_playlist',
# }
# ydl_info_extractor = yt_dlp.YoutubeDL(YDL_INFO_OPTS)


# # ==========================================================
# # PHẦN TẢI VỀ (DOWNLOADER)
# # ==========================================================

# # 1. ĐỊNH NGHĨA NƠI LƯU FILE (QUAN TRỌNG)
# # Đây là nơi file MP3 sẽ được lưu.
# # Hãy thay bằng đường dẫn tuyệt đối trên server của bạn.
# # Ví dụ: '/var/www/my-app/media/' hoặc đọc từ biến môi trường
# AUDIO_SAVE_PATH = os.getenv('AUDIO_SAVE_PATH', '/tmp/audio_files')

# # Tạo thư mục này nếu nó chưa tồn tại
# os.makedirs(AUDIO_SAVE_PATH, exist_ok=True)


# # 2. CẤU HÌNH ĐỂ TẢI MP3
# YDL_DOWNLOAD_OPTS = {
#     'quiet': True,
#     'no_warnings': True,
#     'noplaylist': True,
#     'format': 'bestaudio/best', # Chỉ tải âm thanh tốt nhất
    
#     # Đây là câu trả lời cho "lưu vào đâu":
#     # '%(id)s' sẽ được thay bằng ID của video (ví dụ: dQw4w9WgXcQ)
#     # '%(ext)s' sẽ là 'mp3' (do postprocessor bên dưới)
#     'outtmpl': f'{AUDIO_SAVE_PATH}/%(id)s.%(ext)s',
    
#     # Cấu hình chuyển đổi sang MP3 (Yêu cầu FFmpeg)
#     'postprocessors': [{
#         'key': 'FFmpegExtractAudio',
#         'preferredcodec': 'mp3',
#         'preferredquality': '192', # Chất lượng 192kbps
#     }],
# }

# # 3. TẠO ĐỐI TƯỢNG DOWNLOADER TOÀN CỤC
# ydl_downloader = yt_dlp.YoutubeDL(YDL_DOWNLOAD_OPTS)



# # ==========================================================
# # CẤU HÌNH UPLOAD VÀ GIỚI HẠN
# # ==========================================================
# # Thư mục cơ sở trên Cloudinary
# CLOUDINARY_BASE_FOLDER = "fastapi/test1/audio_files" 
# # Giới hạn kích thước file tải về từ URL (ví dụ: 50MB)
# MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024 # 50MB

# def download_audio(rq: dto.MediaAudioCreateRequest, db: Session) -> dto.MediaAudioResponse:

#     start_time = datetime.now()
#     try:
#         # Giả sử bạn có logic để tải audio từ YouTube hoặc xử lý file audio ở đây
#         # Ví dụ đơn giản: tạo một bản ghi MediaAudio trong database
#         if(rq.input_type not in ['youtube', 'audio_file']):
#             raise BaseException(BaseErrorCode.BAD_REQUEST, message="Invalid input type")
        
#         process_info = None
        
#         if(rq.input_type == 'youtube'):
#             process_info = download_youtube_audio(rq, db)
#         elif(rq.input_type == 'audio_file'):
#             process_info = download_audio_file(rq, db)
            
        
#         # Upload file to Cloudinary
#         file_path = process_info['file_path']
 
#         # Lấy tên file an toàn (video_id hoặc UUID) từ file_path
#         safe_filename = os.path.splitext(os.path.basename(file_path))[0]
#         public_id = f"{CLOUDINARY_BASE_FOLDER}/{safe_filename}"

#         logger.info(f"Đang upload file {file_path} lên cloud as {public_id}...")
#         upload_result = upload_audio_file(file_path, public_id)
#         if not upload_result:
#             raise BaseException(BaseErrorCode.INTERNAL_SERVER_ERROR, message="Upload file lên Cloudinary thất bại.")
#         logger.info(f"File đã được upload lên Cloudinary: {upload_result}")

        
        
#         media_audio = models.MediaAudio(
#             input_url = rq.input_url,
#             input_type = rq.input_type,
#             duration = process_info['duration'] if process_info else 0,
#             title = process_info['title'] if process_info else '',
#             file_path = upload_result,
#         )

#         db.add(media_audio)
#         db.commit()
#         db.refresh(media_audio)
#         print("Đã lưu thông tin MediaAudio vào database.")
#         # Sau khi lưu xong, trả về DTO 
#         return dto.MediaAudioResponse.model_validate(media_audio)
#     except BaseException as be:
#         raise be
#     except Exception as e:
#         raise e
#     finally:
#         # --- BƯỚC 5: DỌN DẸP (LUÔN LUÔN CHẠY) ---
#         # Đảm bảo file tạm luôn bị xóa sau khi xử lý (dù thành công hay lỗi)
#         if file_path and os.path.exists(file_path):
#             try:
#                 os.remove(file_path)
#                 logger.info(f"Đã xóa file tạm: {file_path}")
#             except OSError as e:
#                 # Ghi lại lỗi nhưng không ném ra, vì lỗi chính (nếu có) đã ở trên
#                 logger.error(f"LỖI: Không thể xóa file tạm {file_path}. Lỗi: {e}")
        


# def download_youtube_audio(rq: dto.MediaAudioCreateRequest, db: Session):
#     print("Đang lấy thông tin video...")
    
#     try:
#         # ==========================================================
#         # PHẦN 1: LẤY THÔNG TIN
#         # ==========================================================
#         info = ydl_info_extractor.extract_info(rq.input_url, download=False)
        
#         print("\n--- Thông tin Video ---")
#         print(f"Tiêu đề: {info['title']}")
#         print(f"Thời lượng: {info['duration_string']}")

#         # Kiểm tra thời lượng (sửa lỗi cú pháp của bạn)
#         duration_sec = info.get('duration', 0)
#         if duration_sec > 600: # Lớn hơn 10 phút (600 giây)
#             raise BaseException(BaseErrorCode.BAD_REQUEST, 
#                                 message=f"Video quá dài ({duration_sec}s). Chỉ chấp nhận video dưới 10 phút.")

#         # ==========================================================
#         # PHẦN 2: TẢI FILE MP3
#         # ==========================================================
#         print(f"Video hợp lệ (Thời lượng: {duration_sec}s). Bắt đầu tải...")

#         # Gọi download bằng đối tượng downloader toàn cục
#         # Tác vụ này sẽ block cho đến khi tải và convert xong
#         ydl_downloader.download([rq.input_url])

#         # Xây dựng đường dẫn file cuối cùng (để lưu vào DB)
#         video_id = info.get('id')
#         final_mp3_path = f"{AUDIO_SAVE_PATH}/{video_id}.mp3"
        
#         print(f"Đã tải và convert thành công: {final_mp3_path}")
        
#         # Tạm thời trả về thông tin file đã
#         return {
#             "file_path": final_mp3_path,
#             "title": info.get('title'),
#             "duration": duration_sec
#         }

#     except yt_dlp.utils.DownloadError as e:
#         raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"Lỗi khi xử lý video: {str(e)}")
#     except Exception as e:
#         raise BaseException(BaseErrorCode.INTERNAL_SERVER_ERROR, message=f"Lỗi hệ thống: {str(e)}")

# def download_audio_file(rq: dto.MediaAudioCreateRequest, db: Session):
#     """
#     Tải file audio từ một URL bất kỳ (phiên bản an toàn).
#     """
#     url_audio = rq.input_url
#     logger.info(f"Bắt đầu xử lý file audio từ URL: {url_audio}")
#     try:
#         # --- BƯỚC 1: KIỂM TRA HEADERS (VALIDATION) ---
#         # Gửi HEAD request để kiểm tra trước khi tải
#         # timeout=5: Chờ tối đa 5 giây
#         # allow_redirects=True: Cho phép theo dõi chuyển hướng (vd: http -> https)
#         # with để tự động đóng kết nối sau khi xong
#         with requests.head(url_audio, allow_redirects=True, timeout=5) as head_resp:
#             head_resp.raise_for_status()  # Ném lỗi nếu status không phải 2xx
            
#             # 1.1. Kiểm tra loại file (Content-Type)
#             content_type = head_resp.headers.get('Content-Type', '').lower()
#             if not content_type.startswith('audio/'):
#                 logger.warning(f"URL bị từ chối: Content-Type không phải audio ({content_type})")
#                 raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"URL không trỏ đến file audio (phát hiện: {content_type})")
            
#             # 1.2. Kiểm tra dung lượng (Content-Length)
#             content_length = head_resp.headers.get('Content-Length')
#             if content_length and int(content_length) > MAX_AUDIO_SIZE_BYTES:
#                 file_size_mb = int(content_length) / 1024 / 1024
#                 limit_mb = MAX_AUDIO_SIZE_BYTES / 1024 / 1024
#                 logger.warning(f"URL bị từ chối: File quá lớn ({file_size_mb:.2f} MB)")
#                 raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"File audio quá lớn ({file_size_mb:.2f} MB). Giới hạn: {limit_mb} MB")
#             # --- BƯỚC 2: TẠO TÊN FILE AN TOÀN ---
#             # Lấy đuôi file từ content-type (ví dụ: 'audio/mpeg' -> '.mp3')
#             ext = mimetypes.guess_extension(content_type) or '.dat' # Fallback nếu không đoán được
#             # Tạo tên file duy nhất bằng UUID để tránh trùng lặp
#             filename = f"{uuid.uuid4()}{ext}"
#             save_path = os.path.join(AUDIO_SAVE_PATH, filename)
            
#         # --- BƯỚC 3: TẢI FILE (STREAM) ---
#         logger.info(f"Đang tải file về {save_path}...")
#         # timeout=60: Cho phép tối đa 60 giây để tải
#         with requests.get(url_audio, stream=True, timeout=60) as r_download:
#             r_download.raise_for_status()
#             with open(save_path, 'wb') as f:
#                 for chunk in r_download.iter_content(chunk_size=8192): # Tải từng cục 8KB
#                     if chunk:
#                         f.write(chunk)
#          # --- BƯỚC 4: LẤY THÔNG TIN (DURATION/TITLE) ---
#         # Lấy tên file gốc (an toàn) từ URL để làm 'title'
#         # Ví dụ: http://.../my song.mp3?query=1 -> my song.mp3
#         original_filename = os.path.basename(urlparse(url_audio).path)
#         if not original_filename:
#              original_filename = filename # Fallback về tên file UUID

#         # Lấy duration: Cần FFprobe/FFmpeg (giống yt-dlp). 
#         # Đây là một bước phức tạp, tốn thời gian. Tạm thời để 0.
#         # Nếu bạn CẦN duration, bạn phải gọi 1 lệnh system os.system(f"ffprobe ...")
#         duration_sec = 0
        
#         logger.info(f"Đã tải file audio thành công: {save_path}")
#         return {
#             "file_path": save_path,
#             "title": original_filename,
#             "duration": duration_sec
#         }
#     except requests.exceptions.Timeout:
#         logger.error(f"Lỗi Timeout khi tải file: {url_audio}")
#         raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"Tải file thất bại: Hết thời gian chờ (Timeout)")
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Lỗi khi tải file audio từ URL: {e}")
#         raise BaseException(BaseErrorCode.BAD_REQUEST, message=f"Lỗi tải file audio từ URL: {str(e)}")
#     except BaseException: # Ném lại lỗi BaseException (ví dụ: file quá lớn)
#         raise
#     except Exception as e:
#         logger.error(f"Lỗi không xác định khi tải file: {e}", exc_info=True)
#         raise BaseException(BaseErrorCode.INTERNAL_SERVER_ERROR, message=f"Lỗi hệ thống khi xử lý file: {str(e)}")



# def upload_audio_file(file_path: str, public_id: str):

#     return cloud_service.upload_file(file_path, public_id, resource_type="video")  # audio được coi như video

# def remove_local_file(file_path: str):
#     try:
#         os.remove(file_path)
#         print(f"Đã xóa file tạm thời: {file_path}")
#     except OSError as e:
#         print(f"Lỗi khi xóa file {file_path}: {e.strerror}")