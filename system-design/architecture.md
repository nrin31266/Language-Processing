# Kiến Trúc Hệ Thống - Language Processing Service

## 1. Tổng quan hệ thống

Language Processing Service là backend AI/NLP xử lý các nghiệp vụ liên quan tới audio và ngôn ngữ trong hệ thống học tiếng Anh.

Hệ thống cung cấp 2 nhóm giá trị chính:

- Xử lý online qua API: nhận audio, speech-to-text, phân tích từ theo ngữ cảnh.
- Xử lý pipeline bất đồng bộ: tiếp nhận sự kiện lesson generation, xử lý nhiều bước, publish trạng thái tiến độ.

### Use case chính

- Người dùng upload audio để chấm shadowing.
- Hệ thống tạo bài học từ nguồn audio/video (YouTube hoặc URL file audio).
- Worker xử lý từ vựng hàng loạt: phân tích nghĩa, phiên âm, sinh audio phát âm UK/US.

## 2. Kiến trúc tổng thể

Hệ thống tổ chức theo kiến trúc module hóa gồm các thành phần sau.

### API (routers)

- Nhận request HTTP từ client.
- Validate input.
- Gọi service tương ứng.
- Trả response dạng chuẩn `ApiResponse`.

Các router chính:

- `speech-to-text` router.
- `spacy` router.
- `ai-jobs` router (đang ở mức placeholder).

### Services

Lớp nghiệp vụ trung tâm, bao gồm:

- `speech_to_text_service`: gọi WhisperX và align model.
- `shadowing_service`: so khớp expected words và recognized words.
- `media_service`: tải audio từ YouTube hoặc URL trực tiếp.
- `word_processor`: pipeline phân tích từ + TTS + upload.
- `ai_job_service`: đọc trạng thái hủy job từ Redis.
- `file_service`: tiện ích file/json/text normalization.
- `spaCy_service`: phân tích từ bằng spaCy.

### Workers

- Worker process độc lập (`src/workers/word/word_worker.py`).
- Claim task từ dictionary service qua HTTP API nội bộ.
- Xử lý tuần tự từng task, có sleep để hạn chế quá tải/rate limit.
- Report success/fail về dictionary service.

### Kafka

- Consumer lắng nghe topic `lesson-generation-requested-v1`.
- Producer publish trạng thái sang topic `lesson-processing-step-updated-v1`.
- Dùng cho orchestration pipeline dài, không chặn luồng request HTTP.

### Redis

- Lưu trạng thái AI job (ví dụ `CANCELLED`).
- Consumer kiểm tra trạng thái theo key `aiJobStatus:{aiJobId}` để dừng pipeline sớm.

### S3 Storage (Cloudinary)

- Module `s3_storage` hiện dùng Cloudinary làm object storage.
- Upload file audio và metadata JSON.
- Trả secure URL cho downstream services.

### NLP / Gemini

- `gemini_service` gọi model Gemini qua `google-generativeai`.
- `analyzer` có 2 flow:
  - Analyze sentence batch (IPA UK/US + translation tiếng Việt).
  - Analyze từ đơn (isValid, phonetics, definitions, CEFR).

## 3. Mô tả luồng dữ liệu (data flow)

### 3.1 Luồng API speech-to-text (đồng bộ theo request)

1. Client upload audio + expectedWords.
2. Router validate format file và payload.
3. Service ghi file tạm.
4. WhisperX transcribe + align.
5. Shadowing service so sánh expected vs recognized.
6. Trả response gồm segment, text và shadowingResult.
7. Xóa file tạm.

### 3.2 Luồng lesson generation (bất đồng bộ qua Kafka)

1. Kafka Consumer nhận `LessonGenerationRequestedEvent`.
2. Tải metadata cũ (nếu có) từ URL JSON.
3. Step SOURCE_FETCHED:
   - Download audio từ YouTube hoặc URL.
   - Upload audio lên Cloudinary.
   - Lưu metadata mới.
4. Step TRANSCRIBED:
   - Gọi WhisperX transcribe.
   - Lưu metadata transcription.
5. Step NLP_ANALYZED:
   - Chia chunk câu.
   - Gọi Gemini phân tích theo batch.
   - Lưu metadata NLP.
6. Step COMPLETED hoặc FAILED.
7. Mỗi bước đều publish event tiến độ ra Kafka.
8. Trước/sau các bước quan trọng, kiểm tra trạng thái CANCELLED trong Redis để dừng sớm.

### 3.3 Luồng Word Worker

1. Worker claim danh sách task từ dictionary service.
2. Với từng word:
   - Gọi Gemini analyze word.
   - Nếu hợp lệ: generate audio UK/US qua Google TTS.
   - Upload audio lên Cloudinary.
   - Gắn URL vào payload kết quả.
3. Report success/fail.

## 4. Luồng xử lý chính (flow)

Ví dụ flow tổng quát pipeline lesson:

Request tạo bài học
-> API nguồn phát event
-> Kafka (`lesson-generation-requested-v1`)
-> Consumer `handle_lesson_generation_requested`
-> Services (media, speech_to_text, gemini)
-> Cloudinary (audio + metadata)
-> Redis check cancel
-> Kafka (`lesson-processing-step-updated-v1`)
-> Service downstream cập nhật trạng thái cho client

Ví dụ flow worker:

Dictionary Service
-> Worker claim task
-> Gemini analyze
-> Google TTS
-> Cloudinary upload
-> Callback success/fail về Dictionary Service

## 5. Mô tả từng module

### `auth/`

- Cấu hình Keycloak issuer URI.
- Verify JWT bằng JWKS.
- Trích xuất user principal và role.
- Cung cấp dependency kiểm tra đăng nhập/quyền cho router.

### `routers/`

- Tầng giao tiếp HTTP.
- Gồm router cho AI job, speech-to-text, spaCy.
- Chuẩn hóa response theo DTO chung.

### `services/`

- Chứa business logic chính.
- Tách biệt với router để dễ test và tái sử dụng.
- Bao phủ media download, transcription, NLP, shadowing, word pipeline.

### `workers/`

- Process nền chạy độc lập.
- Khả năng chạy nhiều instance song song bằng script.
- Phù hợp tác vụ nặng hoặc tác vụ hàng đợi.

### `kafka/`

- Định nghĩa producer/consumer/event/topic.
- Xử lý event bất đồng bộ giữa các service.
- Đảm bảo pipeline dài không block API realtime.

### `redis/`

- Async redis client.
- Lưu trạng thái runtime của AI job.
- Cho phép cơ chế cancel graceful trong pipeline.

### `s3_storage/`

- Abstraction layer upload file/json.
- Hiện thực bằng Cloudinary.
- Trả về secure URL để truyền qua event/metadata.

### `gemini/`

- Cấu hình model và API key.
- Prompt template cho sentence/word analysis.
- Validate output JSON để giảm lỗi định dạng từ model.

### `tts/`

- Build SSML từ word + IPA.
- Sinh audio UK/US qua Google Cloud Text-to-Speech.
- Chạy async bằng `asyncio.to_thread`.

## 6. Diagram (ASCII)

```text
                        +--------------------+
                        |      Client        |
                        +---------+----------+
                                  |
                                  v
                     +------------+-------------+
                     |      FastAPI Routers     |
                     |  (speech, spacy, ai-job) |
                     +------+--------------+-----+
                            |              |
                            | sync         | async event-driven
                            v              v
               +------------+----+   +-----+--------------------+
               |   Services      |   | Kafka Producer/Consumer  |
               | (STT/NLP/Media) |   +-----+--------------------+
               +------+----------+         |
                      |                    v
                      |            +-------+--------+
                      |            |  Workers/Flow  |
                      |            | lesson + word  |
                      |            +---+--------+---+
                      |                |        |
                      v                v        v
            +---------+---------+   +--+--+  +--+----------------+
            |   Cloudinary      |   |Redis|  | Gemini + Google TTS|
            | (audio, metadata) |   |state|  | WhisperX + spaCy   |
            +-------------------+   +-----+  +---------------------+
```

## 7. Khả năng scale

### Scale workers

- `run_word_worker.sh` cho phép tăng số process worker theo nhu cầu.
- Có thể triển khai nhiều worker instance trên nhiều node để tăng throughput.

### Scale API

- API stateless, có thể scale ngang bằng nhiều instance Uvicorn/Gunicorn.
- Tách xử lý nặng qua Kafka/worker giúp giảm tải request-response trực tiếp.

### Scale async pipeline với Kafka

- Kafka giúp tách producer và consumer, chịu tải burst tốt hơn.
- Có thể mở rộng theo partition/consumer group khi lưu lượng tăng.
- Publish trạng thái từng bước giúp quan sát pipeline và retry ở downstream.

## 8. Ghi chú thiết kế

- Eureka registration đang có sẵn module nhưng chưa bật trong `main.py`.
- Kafka bootstrap server và một số thông số đang hard-code (nên đưa ra env cho production).
- TTS router hiện chưa expose endpoint hoàn chỉnh dù service đã sẵn sàng.
- Phần worker hiện xử lý tuần tự theo từng job; có thể nâng cấp concurrency theo batch trong tương lai.