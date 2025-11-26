# src/kafka/consumer.py

import asyncio
import json
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
from src.s3_storage import cloud_service
from src.services import ai_job_service
from src.services.lesson_service import lessonParseAiMetaData
from src.services.file_service import fetch_json_from_url
async def handleLessonGenerationRequested(event: LessonGenerationRequestedEvent):
    """Xử lý khi có yêu cầu tạo bài học."""
    print(f"📥 Nhận LessonGenerationRequestedEvent: {event}")
    try:
        # Cho 3s cho hệ thống ổn định
        await asyncio.sleep(3)
        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        isSkip = False
        metadata : dto.AiMetadataDto = None
        try:
            fileMetadata = await fetch_json_from_url(event.ai_meta_data_url)
            metadata = lessonParseAiMetaData(fileMetadata)
            print(f"✅ Fetched AI meta data from URL {event.ai_meta_data_url}: {metadata}")
        except Exception as e:
            print(f"❌ Failed to fetch AI meta data from URL {event.ai_meta_data_url}: {e}")
            metadata = dto.AiMetadataDto()   # Tạo object rỗng để tránh None

        
        
        
        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        
        if metadata.source_fetched is None or event.is_restart == True:
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
            if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
                print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
                return
            uploadUrl = cloud_service.upload_file(
                audio_info.file_path,
                public_id= f"lps/lessons/audio/{audio_info.sourceReferenceId}",
                resource_type= "video" 
            )
            audio_info.audioUrl = uploadUrl
            metadata.source_fetched = audio_info.model_dump(by_alias=True)
            metadataUploadUrl = cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True)),
                public_id= f"lps/lessons/{event.lesson_id}/ai-metadata",
            )
            print(f"✅ Đã tải audio cho Lesson voi {event.ai_job_id}, file tại: {audio_info.file_path}")
        else:
            audio_info = dto.AudioInfo.model_validate(metadata.source_fetched)
            print(f"✅ Sử dụng lại audio_info từ AI meta data cho Lesson voi {event.ai_job_id}: {audio_info}")
            uploadUrl = audio_info.audioUrl
            isSkip = True
            metadataUploadUrl = event.ai_meta_data_url
        
        
        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        
            
            
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiJobId=event.ai_job_id,
                processingStep=LessonProcessingStep.SOURCE_FETCHED,
                audioUrl=uploadUrl,
                sourceReferenceId=audio_info.sourceReferenceId,
                aiMessage="Audio source fetched successfully.",
                thumbnailUrl=audio_info.thumbnailUrl,
                isSkip=isSkip,
                aiMetadataUrl=metadataUploadUrl,
            )
        )
        isSkip = False
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

