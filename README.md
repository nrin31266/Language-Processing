📄 README.md 
# Language Processing Service

## 1. Giới thiệu dự án
Language Processing Service (LPS) là backend service xây dựng bằng FastAPI, phục vụ các bài toán xử lý ngôn ngữ và audio cho hệ thống học tiếng Anh. Dự án tích hợp nhiều thành phần như Speech-to-Text, NLP, Gemini AI, Text-to-Speech, hàng đợi bất đồng bộ qua Kafka, cache/trạng thái qua Redis, và lưu trữ file qua Cloudinary.

## 2. Mục đích hệ thống
Hệ thống tập trung vào các mục tiêu chính:

- Chuyển giọng nói thành văn bản và đánh giá shadowing.
- Phân tích ngôn ngữ (từ, câu) phục vụ học ngoại ngữ.
- Sinh audio phát âm UK/US cho từ vựng.
- Xử lý pipeline dài theo hướng bất đồng bộ, có thể mở rộng bằng worker.

## 3. Tính năng chính

- API `speech-to-text`:
	- Nhận file audio upload.
	- Dùng WhisperX để nhận diện.
	- So khớp expected words và trả về kết quả shadowing.
- API `spacy`:
	- Phân tích từ theo ngữ cảnh (lemma, POS, tag, dependency, entity type).
- API `ai-jobs`:
	- Tạo placeholder AI job response.
- Kafka Consumer Pipeline:
	- Lắng nghe sự kiện tạo lesson.
	- Tải audio nguồn (YouTube/audio URL), upload cloud, transcribe, NLP analyze bằng Gemini.
	- Publish trạng thái từng bước xử lý.
- Word Worker:
	- Claim task từ dictionary service.
	- Phân tích từ bằng Gemini.
	- Generate audio UK/US bằng Google Cloud TTS.
	- Upload audio lên Cloudinary và callback kết quả.

## 4. Kiến trúc tổng quan

- API Layer: FastAPI routers nhận request và trả response chuẩn `ApiResponse`.
- Service Layer: Chứa business logic cho media, speech, NLP, word processing, ai job.
- Messaging Layer: Kafka producer/consumer cho pipeline bất đồng bộ.
- Worker Layer: Worker xử lý từ vựng chạy độc lập, scale theo số process.
- Storage/State Layer:
	- Redis: lưu trạng thái hủy AI job.
	- Cloudinary: lưu audio và metadata JSON.
- AI/NLP Layer:
	- WhisperX cho speech-to-text.
	- spaCy cho phân tích ngôn ngữ.
	- Gemini cho phân tích câu/từ.
	- Google Cloud TTS cho text-to-speech.

## 5. Cấu trúc thư mục

```text
.
├── src/
│   ├── main.py                  # Entry point FastAPI, startup/shutdown lifecycle
│   ├── routers/                 # Định nghĩa API endpoints
│   ├── services/                # Business logic
│   ├── workers/word/            # Worker xử lý từ vựng
│   ├── kafka/                   # Producer, consumer, topic, event models
│   ├── redis/                   # Redis config + async client
│   ├── s3_storage/              # Upload file/json lên Cloudinary
│   ├── gemini/                  # Gemini config, prompts, analyzer
│   ├── tts/                     # TTS service (Google Cloud Text-to-Speech)
│   ├── auth/                    # JWT/Keycloak authentication + dependencies
│   ├── client/                  # HTTP client đến dictionary service
│   ├── discovery_client/        # Eureka client registration
│   ├── errors/                  # Error code, exception, global handlers
│   ├── utils/                   # Tiện ích chung (chunking, text normalize)
│   ├── dto.py                   # DTO/Pydantic models dùng toàn hệ thống
│   ├── enum.py                  # Enum cho source type và processing step
│   └── temp/                    # Thư mục file tạm (audio, shadowing, json)
├── logs/                        # Log runtime của worker
├── run.sh                       # Script chạy API server
├── run_word_worker.sh           # Script chạy nhiều word worker
├── requirements.txt             # Danh sách dependencies Python
├── .env_example                 # Mẫu biến môi trường
└── system-design/
		└── architecture.md          # Tài liệu kiến trúc chi tiết
```

## 6. Công nghệ sử dụng

### Backend Framework
- FastAPI
- Uvicorn

### Auth/Security
- python-jose[cryptography]
- cryptography
- authlib

### Messaging và Integration
- confluent-kafka
- py-eureka-client
- redis
- httpx

### AI/NLP/Speech
- whisperx
- librosa
- google-generativeai
- spacy
- en_core_web_sm
- google-cloud-texttospeech

### Media/Storage
- cloudinary
- yt-dlp

### Utilities
- python-dotenv
- pydantic-settings
- python-multipart
- orjson
- tenacity
- numpy, thinc

## 7. Hướng dẫn cài đặt

### 7.1 Chuẩn bị môi trường

- Python 3.12 (khuyến nghị theo môi trường hiện tại).
- Kafka broker chạy tại `localhost:9092`.
- Redis server.
- Tài khoản Cloudinary.
- API key Gemini.
- Google Cloud credentials cho TTS.

### 7.2 Tạo và kích hoạt virtual environment

```bash
python3 -m venv lps-env
source lps-env/bin/activate
```

### 7.3 Cài dependencies

```bash
pip install -r requirements.txt
```

### 7.4 Cấu hình biến môi trường

```bash
cp .env_example .env
```

Sau đó điền giá trị thật trong `.env`.

## 8. Hướng dẫn chạy

### 8.1 Chạy API bằng `run.sh`

```bash
chmod +x run.sh
./run.sh
```

Script sẽ:
- Activate virtual environment `lps-env`.
- Chạy FastAPI với Uvicorn tại `0.0.0.0:8089`.

### 8.2 Chạy Word Worker bằng `run_word_worker.sh`

```bash
chmod +x run_word_worker.sh
./run_word_worker.sh
```

Script sẽ:
- Hỏi số lượng worker cần chạy.
- Spawn nhiều process `python -m src.workers.word.word_worker`.
- Ghi log vào `logs/word_worker_<n>.log`.
- Tự `tail -f` log worker 1.

### 8.3 Quản lý worker logs

```bash
# Xem realtime
tail -f logs/word_worker_1.log

# Xem toàn bộ log
cat logs/word_worker_1.log

# Xem 50 dòng cuối
tail -n 50 logs/word_worker_1.log

# Kiểm tra worker đang chạy
pgrep -af word_worker

# Dừng tất cả worker
pkill -f word_worker
```

## 9. Biến môi trường (.env)

Các biến chính hệ thống đang sử dụng:

```bash
# Auth / Keycloak
KEYCLOAK_ISSUER_URI=http://localhost:8080/realms/demo-realm

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Redis
REDIS_URL=redis://localhost:6379/0

# Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Dictionary worker integration
DICTIONARY_SERVICE_URL=http://localhost:8080
WORKER_API_KEY=

# Speech / Media
ENABLE_WHISPERX=1
AUDIO_SAVE_PATH=src/temp/audio_files

# Google TTS credentials
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google_tts_key.json

# Optional TTS setting
TTS_DEFAULT_VOICE=us
```

Gợi ý:
- Không commit `.env` chứa secret thật.
- Dùng `.env_example` để chia sẻ format cấu hình cho team.

## 10. Tài liệu kiến trúc

Xem chi tiết tại:

- `system-design/architecture.md`