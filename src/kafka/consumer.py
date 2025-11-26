# src/kafka/consumer.py

import asyncio
import json
import os
from src.kafka.config import create_kafka_consumer
from src.kafka.event import (
    LessonGenerationRequestedEvent,
    LessonProcessingStepUpdatedEvent
)
from src.kafka.producer import (
    publish_lesson_processing_step_updated
)
from src.enum import LessonProcessingStep, LessonSourceType
from confluent_kafka import KafkaError
from src.kafka.topic import LESSON_GENERATION_REQUESTED_TOPIC, LESSON_PROCESSING_STEP_UPDATED_TOPIC
import uuid
from src import dto
from src.services import media_service
from src.utils import fileUtils
from src.s3_storage import cloud_service
from src.services import ai_job_service
async def handleLessonGenerationRequested(event: LessonGenerationRequestedEvent):
    """Xử lý khi có yêu cầu tạo bài học."""
    print(f"📥 Nhận LessonGenerationRequestedEvent: {event}")
    try:
        # Cho 3s cho hệ thống ổn định
        await asyncio.sleep(5)
        if ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        # STEP 1: Download audio từ source_url
        audio_info = None
        uploadUrl = None
        if( event.source_type == LessonSourceType.youtube):
            audio_info =  media_service.download_youtube_audio(
                dto.MediaAudioCreateRequest(
                    input_url=event.source_url
                )
            )
        elif( event.source_type == LessonSourceType.audio_file):
            audio_info =  media_service.download_audio_file(
                dto.MediaAudioCreateRequest(
                    input_url=event.source_url
                )
            )
        else:
            raise Exception(f"Unsupported LessonSourceType: {event.source_type}")
        print(f"✅ Đã tải audio cho Lesson voi {event.ai_job_id}, file tại: {audio_info.file_path}")
        
        if ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        
        fileUtils.save_json(audio_info.model_dump(by_alias=True), f"lesson_" + audio_info.sourceReferenceId + "_audio_info")
        uploadUrl = cloud_service.upload_file(
            audio_info.file_path,
            public_id= f"lps/lessons/audio/{audio_info.sourceReferenceId}",
            resource_type= "video" 
        )
        
        if ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
            
            
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiJobId=event.ai_job_id,
                processingStep=LessonProcessingStep.SOURCE_FETCHED,
                audioUrl=uploadUrl,
                sourceReferenceId=audio_info.sourceReferenceId,
                aiMessage="Audio source fetched successfully.",
                thumbnailUrl=audio_info.thumbnailUrl
            )
        )
        print(f"✅ Đã gửi LessonProcessingStepUpdatedEvent SOURCE_FETCHED cho Lesson với ai_job_id: {event.ai_job_id}")
        # STEP 2: Xử ly audio bằng AI
        # STEP 3: NLP analysis
    except Exception as e:
        print(f"⚠️ Lỗi khi xử lý LessonGenerationRequestedEvent: {e}")
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiMessage=f"Lesson generation failed: {e}",
                processingStep=LessonProcessingStep.FAILED,
                aiJobId=event.ai_job_id,
            )
        )

async def consume_events():
    """
    Một consumer duy nhất lắng nghe TẤT CẢ các topic nghiệp vụ.
    """
    topics = [LESSON_GENERATION_REQUESTED_TOPIC]
    
    # Chạy hàm blocking `create_kafka_consumer` trong thread riêng
    consumer = await asyncio.to_thread(create_kafka_consumer, topics)
    print(f"🚀 Kafka consumer (gộp) đã khởi động, lắng nghe: {topics}")

    try:
        while True:
            # Chạy hàm blocking `poll` trong thread riêng
            # Event loop chính hoàn toàn rảnh để xử lý API (0.27ms)
            msg = await asyncio.to_thread(consumer.poll, 0.1) # 100ms timeout
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Kafka error: {msg.error()}")
                continue
            
            # Xác định xem event đến từ topic nào
            topic = msg.topic()

            try:
                payload = json.loads(msg.value().decode("utf-8"))

                # Phân luồng nghiệp vụ dựa trên topic
                if topic == LESSON_GENERATION_REQUESTED_TOPIC:
                    event = LessonGenerationRequestedEvent(**payload)
                    asyncio.create_task(
                        handleLessonGenerationRequested(event)
                    )

            except Exception as e:
                print(f"⚠️ Lỗi xử lý message (topic: {topic}): {e}")

    except asyncio.CancelledError:
        print("📪 Đang dừng consumer...")
    finally:
        # Chạy hàm blocking `close` trong thread riêng
        await asyncio.to_thread(consumer.close)
        print("📪 Consumer đã dừng.")


async def start_kafka_consumers():
    """
    Hàm này được gọi bởi `lifespan` trong `main.py`
    """
    # Chỉ cần chạy 1 consumer gộp duy nhất
    await consume_events()

# # -----------------------------------------------------------------
# # 1. BẢO VỆ DATABASE: Giới hạn số tác vụ chạy song song
# # -----------------------------------------------------------------
# # Đặt con số này gần bằng với connection pool của CSDL (ví dụ: 20)
# # Điều này đảm bảo không bao giờ mở quá 20 session CSDL cùng lúc.
# CONCURRENT_TASK_LIMIT = 20
# db_semaphore = asyncio.Semaphore(CONCURRENT_TASK_LIMIT)


# async def run_handler_with_limit(handler, event):
#     """
#     Một "cổng" kiểm soát: phải lấy được 1 vé (semaphore) thì mới cho chạy handler.
#     Việc này đảm bảo CSDL không bị quá tải.
#     """
#     async with db_semaphore:
#         # Khi đã có "vé", chạy handler (ví dụ: handle_order_created_event)
#         await handler(event)

# # -----------------------------------------------------------------
# # 2. HANDLERS: Logic xử lý nghiệp vụ (giữ nguyên)
# # -----------------------------------------------------------------

# async def handle_order_created_event(event: OrderCreatedEvent):
#     """Xử lý khi có đơn hàng được tạo."""
#     db = SessionLocal()
#     print(f"📥 Nhận OrderCreatedEvent: {event.order_id}")
#     try:
#         # Giả lập giữ hàng
#         if product_repository.decrease_stock_if_available(
#             event.product_id, event.quantity, db
#         ):
#             # Lưu thông tin đơn hàng đã giữ hàng
#             reserved_order_repository.insert_if_not_exists(
#                 db, event.order_id, event.product_id, event.quantity
#             )
#             print(f"✅ Đã giữ hàng cho Order {event.order_id}")
            
#             # Gửi event thành công (đã await)
#             await publish_inventory_reserved(
#                 InventoryReservedEvent(
#                     order_id=event.order_id,
#                     status="RESERVED",
#                     message="Hàng đã được giữ thành công.",
#                 )
#             )
#         else:
#             # Gửi event thất bại (đã await)
#             await publish_inventory_failed(
#                 InventoryFailedEvent(
#                     order_id=event.order_id, 
#                     status="FAILED", 
#                     message="Không đủ hàng trong kho."
#                 )
#             )
#     except Exception as e:
#         print(f"❌ Giữ hàng thất bại (Order {event.order_id}): {e}")
#         await publish_inventory_failed(
#             InventoryFailedEvent(
#                 order_id=event.order_id, status="FAILED", message=str(e)
#             )
#         )
#     finally:
#         db.close() # Rất quan trọng: Luôn đóng session sau khi xong


# async def handle_order_cancelled_event(event: OrderCancelledEvent):
#     """Xử lý khi đơn hàng bị hủy."""
#     db = SessionLocal()
#     print(f"📥 Nhận OrderCancelledEvent: {event.order_id}")
#     try: # Bọc trong try/finally để đảm bảo db được đóng
#         reserved_order = reserved_order_repository.get_by_order_id_and_product_id(
#             db, event.order_id, event.product_id
#         )
#         if reserved_order:
#             # Hoàn trả hàng
#             product_repository.increase_stock(db, event.product_id, reserved_order.quantity)
#             reserved_order_repository.delete_reserved_order(db, event.order_id, event.product_id)
#             print(f"✅ Đã hoàn trả hàng cho Order {event.order_id}")
#     except Exception as e:
#          print(f"❌ Hủy hàng thất bại (Order {event.order_id}): {e}")
#     finally:
#         db.close() # Rất quan trọng: Luôn đóng session sau khi xong

# # -----------------------------------------------------------------
# # 3. CONSUMER: Gộp 2 consumer thành 1
# # -----------------------------------------------------------------
