# main.py
import logging
from typing import Optional
from fastapi import FastAPI, Depends, status, Response, HTTPException
from pydantic import BaseModel
from uvicorn import run
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src import dto
from src.errors.base_exception_handler import (
    base_exception_handler,
    global_exception_handler,
    http_exception_handler
)
from src.errors.base_exception import BaseException

from src.discovery_client.eureka_config import (
    register_with_eureka,
)  # Đảm bảo import này đúng
from src.kafka.consumer import start_kafka_consumers
from src.kafka.producer import periodic_flush, producer
# StarletteHTTPException
from fastapi.exceptions import HTTPException
import asyncio
# cloud
from src.cloud.config import setup_cloudinary
# --- 1. Cấu hình logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
import gc
import torch
from src.redis.redis_client import redis_client
# --- 2. Định nghĩa Lifespan (cho Eureka) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Khi app START ---
    
    # --- GỌI CẤU HÌNH CLOUDINARY Ở ĐÂY ---
    setup_cloudinary()
    print("🔌 Connecting Redis...")
    try:
        await redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print("❌ Redis connection failed:", e)
    # await register_with_eureka()
    print("✅ Registered with Eureka")
    # asyncio.create_task(start_kafka_consumers())
    # print("📡 Kafka consumers started")
    # Khởi chạy Kafka consumers trong background
    kafka_task = asyncio.create_task(start_kafka_consumers())
    flush_task = asyncio.create_task(periodic_flush())  # Thêm periodic flush
    
    print("📡 Kafka consumers started")
    yield  # 👉 FastAPI chạy trong khoảng này

     # --- Khi app SHUTDOWN ---
    print("🧹 Shutting down FastAPI...")
    kafka_task.cancel()
    flush_task.cancel()
    try:
        await kafka_task
        await flush_task
    except asyncio.CancelledError:
        pass
    producer.flush(10)  # Flush cuối cùng
    
    
    # 🧹 DỌN CLEANUP WHISPERX + PYTORCH GPU
    print("🧽 Cleaning WhisperX & GPU memory...")
    from src.services.speech_to_text_service import whisper_model

    try:
        del whisper_model
    except:
        pass
    
    # Xóa luôn các model alignment nếu có (trong RAM/GPU)
    try:
        from whisperx import alignment
        alignment.alignment_model = None
    except:
        pass

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    print("✅ WhisperX model unloaded & GPU memory cleaned.")


# --- 3. Tạo FastAPI App (CHỈ MỘT LẦN) ---
app = FastAPI(
    title="FastAPI Service",
    lifespan=lifespan,
)

# --- 4. Thêm Middleware (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 6. Include các Routers ---
from src.routers import media_router, speech_to_text, redis_router
app.include_router(media_router.router)
app.include_router(speech_to_text.router)
app.include_router(redis_router.router)
# app.include_router(blog.router)
# app.include_router(user.router)
# app.include_router(auth.router)

# --- 5. Đăng ký Exception Handlers ---
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(BaseException, base_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)




# --- 8. Thêm các route gốc (Health check, Info) ---
@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/info")
def info():
    return {"service": "inventory-service", "version": "1.0.0"}
