from dotenv import load_dotenv
load_dotenv()
import logging
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.errors.base_exception_handler import (
    base_exception_handler,
    global_exception_handler,
    http_exception_handler
)
from src.errors.base_exception import BaseException

from src.discovery_client.eureka_config import (
    register_with_eureka,
) 
from src.kafka.consumer.consumer import start_kafka_consumers
from src.kafka.producer import periodic_flush, producer
from fastapi.exceptions import HTTPException
import asyncio
# cloud
from src.s3_storage.config import setup_cloudinary
# Cấu hình logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
import gc
import torch
from src.redis.redis_client import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Khi app START ---
    
   
    setup_cloudinary()
    print("Connecting Redis...")
    try:
        await redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print("❌ Redis connection failed:", e)
    # Đăng ký với Eureka
    # await register_with_eureka()
    print("✅ Registered with Eureka")
    # Khởi chạy Kafka consumers trong background
    kafka_task = asyncio.create_task(start_kafka_consumers())
    flush_task = asyncio.create_task(periodic_flush())  # Thêm periodic flush
    
    print("✅ Kafka consumers started")
    yield  

     # Khi app SHUTDOWN 
    print("Shutting down FastAPI...")
    kafka_task.cancel()
    flush_task.cancel()
    try:
        await kafka_task
        await flush_task
    except asyncio.CancelledError:
        pass
    producer.flush(10)  # Flush trước khi đóng
    
    
    #  DỌN CLEANUP WHISPERX + PYTORCH GPU
    print("Cleaning WhisperX & GPU memory...")
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


# Setup FastAPI app
app = FastAPI(
    title="FastAPI Service",
    lifespan=lifespan,
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
from src.routers import tts_router, dictionary_router, ai_job_router, speech_to_text_router
app.include_router(speech_to_text_router.router)
app.include_router(ai_job_router.router)
app.include_router(tts_router.router)
app.include_router(dictionary_router.router)


# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(BaseException, base_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)




# Register root routes (Health check, Info)
@app.get("/health")
def health():
    return {"status": "UP"}
@app.get("/info")
def info():
    return {"service": "inventory-service", "version": "1.0.0"}
