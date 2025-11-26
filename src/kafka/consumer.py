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
from typing import List
from src import dto
from src.services import media_service
from src.s3_storage import cloud_service
from src.services import ai_job_service
from src.services import file_service
from src.services.lesson_service import lessonParseAiMetaData
from src.services.file_service import fetch_json_from_url, file_exists
from src.services import speech_to_text_service
from src.services import batch_service
from src.utils.chunk_utils import chunk_list

async def handleLessonGenerationRequested(event: LessonGenerationRequestedEvent):
    """Xử lý khi có yêu cầu tạo bài học."""
    print(f"📥 Nhận LessonGenerationRequestedEvent: {event}")
    try:
        # Cho 2s cho hệ thống ổn định
        await asyncio.sleep(2)
        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        isSkip = False
        metadata : dto.AiMetadataDto = None
        try:
            fileMetadata = await fetch_json_from_url(event.ai_meta_data_url)
            metadata = dto.AiMetadataDto.model_validate(fileMetadata)
            print(f"✅ Fetched AI meta data from URL {event.ai_meta_data_url}")
            # print(f"🔍 AI Meta Data: {metadata.model_dump()}")
        except Exception as e:
            metadata = dto.AiMetadataDto()   # Tạo object rỗng để tránh None

        audio_info = None
        uploadUrl = None
        metadataUploadUrl = event.ai_meta_data_url if event.ai_meta_data_url else None
        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        
        if metadata.sourceFetched is None or event.is_restart:
            # STEP 1: Download audio từ source_url
            
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
            metadata.sourceFetched = dto.SourceFetchedDto.model_validate(
                audio_info.model_dump(by_alias=True)
            )
        
            metadataUploadUrl = cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True)),
                public_id= f"lps/lessons/{event.lesson_id}/ai-metadata",
            )
            print(f"✅ Đã tải audio cho Lesson voi {event.ai_job_id}, file tại: {audio_info.file_path}")
        else:
            audio_info = dto.AudioInfo.model_validate(metadata.sourceFetched)
            print(f"🔁 Sử dụng lại audio_info từ AI meta data cho Lesson voi {event.ai_job_id}: {audio_info}")
            uploadUrl = audio_info.audioUrl
            isSkip = True
            metadataUploadUrl = event.ai_meta_data_url
            # Kiểm tra file audio có tồn tại không
            if not file_exists(audio_info.file_path):
                print(f"⚠️ File audio local không tồn tại tại {audio_info.file_path}, sẽ tải lại từ source_url. Download lại.")
                audio_info.file_path =  media_service.download_audio_file(
                    dto.MediaAudioCreateRequest(
                        input_url=audio_info.audioUrl,
                        audio_name=audio_info.sourceReferenceId
                    )
                ).file_path
    
        if( metadata.sourceFetched.duration is None):
            metadata.sourceFetched.duration = int(speech_to_text_service.get_audio_duration(audio_info.file_path))
            print(f"🔍 Lấy duration cho audio tại {audio_info.file_path}. Duration: {metadata.sourceFetched.duration}")

        
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
                # always int 
                durationSeconds=metadata.sourceFetched.duration if metadata.sourceFetched.duration else 0
            )
        )
        isSkip = False
        print(f"✅ Đã gửi LessonProcessingStepUpdatedEvent sourceFetched cho Lesson với ai_job_id: {event.ai_job_id}")
        # STEP 2: Xử ly audio bằng AI
        transcription_result: dto.TranscribedDto = None
        if( metadata.transcribed is None or event.is_restart):
            print(f"🔍 Bắt đầu transcribe audio cho Lesson với ai_job_id: {event.ai_job_id}")
            transcription_result = speech_to_text_service.transcribe(
                audio_info.file_path,
            )
        
            metadata.transcribed = dto.TranscribedDto.model_validate(transcription_result)
            transcription_result = metadata.transcribed
            print(f"✅ Audio transcribed for Lesson with ai_job_id: {event.ai_job_id}")
            # Cập nhật lại metadata lên cloud tra ve cung duong dan cu
            metadataUploadUrl = cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True), ensure_ascii=False),
                public_id= f"lps/lessons/{event.lesson_id}/ai-metadata",
            )
            print(f"✅ Cập nhật AI meta data lên {metadataUploadUrl} cho Lesson với ai_job_id: {event.ai_job_id}")
        else:
            print(f"🔁 Sử dụng lại transcription từ AI meta data cho Lesson voi {event.ai_job_id}")
            isSkip = True
            transcription_result = metadata.transcribed
        
        if( await ai_job_service.aiJobWasCancelled(event.ai_job_id)):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiJobId=event.ai_job_id,
                processingStep=LessonProcessingStep.TRANSCRIBED,
                aiMessage="Audio transcribed successfully.",
                audioUrl=uploadUrl,
                isSkip=isSkip,
                aiMetadataUrl=metadataUploadUrl,
            )
        )
        isSkip = False
        print(f"✅ Đã gửi LessonProcessingStepUpdatedEvent TRANSCRIBED cho Lesson với ai_job_id: {event.ai_job_id}")
        
        # STEP 3: NLP analysis
        nlp_result: dto.NlpAnalyzedDto = None

        segments = transcription_result.segments
        nlp_sentences: List[dto.SentenceAnalyzedDto] = []
        batch_size = 5

        # Build payload với index chuẩn
        sentences_payload = [
            {"orderIndex": idx, "text": seg.text}
            for idx, seg in enumerate(segments)
        ]


        if metadata.nlpAnalyzed is None or event.is_restart:
            print(f"🔍 Bắt đầu NLP analysis cho Lesson với ai_job_id: {event.ai_job_id}")

            for chunk in chunk_list(sentences_payload, batch_size):

                # 1) Check cancel trước mỗi batch
                if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
                    print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng NLP.")
                    return

                print(f"🧠 NLP batch {chunk[0]['orderIndex']} → {chunk[-1]['orderIndex']} running...")
                # 2) Gửi batch sang Gemini
                batch_output = await batch_service.analyze_sentence_batch(chunk)

                # 3) Convert sang DTO
                for item in batch_output:
                    nlp_sentences.append(dto.SentenceAnalyzedDto(**item))

                await asyncio.sleep(0.1)   # giảm spam API

            # Full NLP result
            nlp_result = dto.NlpAnalyzedDto(sentences=nlp_sentences)

            # Lưu vào metadata
            metadata.nlpAnalyzed = dto.NlpAnalyzedDto.model_validate(nlp_result.model_dump())

            # Upload metadata mới
            metadataUploadUrl = cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True), ensure_ascii=False),
                public_id=f"lps/lessons/{event.lesson_id}/ai-metadata",
            )

            print(f"✅ NLP analysis hoàn thành và đã upload metadata lên {metadataUploadUrl}")

            await publish_lesson_processing_step_updated(
                LessonProcessingStepUpdatedEvent(
                    aiJobId=event.ai_job_id,
                    processingStep=LessonProcessingStep.NLP_ANALYZED,
                    aiMessage="NLP analysis completed successfully.",
                    aiMetadataUrl=metadataUploadUrl,
                    isSkip=False
                )
            )

        else:
            print(f"🔁 Sử dụng lại NLP metadata cho ai_job_id: {event.ai_job_id}")
            nlp_result = dto.NlpAnalyzedDto.model_validate(metadata.nlpAnalyzed)

            await publish_lesson_processing_step_updated(
                LessonProcessingStepUpdatedEvent(
                    aiJobId=event.ai_job_id,
                    processingStep=LessonProcessingStep.NLP_ANALYZED,
                    aiMessage="NLP reused from previous metadata.",
                    aiMetadataUrl=event.ai_meta_data_url,
                    isSkip=True
                )
            )
        print(f"✅ Đã gửi LessonProcessingStepUpdatedEvent nlpAnalyzed cho Lesson với ai_job_id: {event.ai_job_id}")
        # Cho 2s cho hệ thống ổn định, sau do gui complete
        await asyncio.sleep(2)
        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiJobId=event.ai_job_id,
                processingStep=LessonProcessingStep.COMPLETED,
                aiMessage="Lesson generation completed successfully.",
                aiMetadataUrl=metadataUploadUrl,
                isSkip=False
            )
        )
    except Exception as e:
        print(f"⚠️ Lỗi khi xử lý LessonGenerationRequestedEvent: {e}")
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiMessage=f"Lesson generation failed: {e}",
                processingStep=LessonProcessingStep.FAILED,
                aiJobId=event.ai_job_id,
            )
        )
    finally:
        # Dọn dẹp file local, try except để đảm bảo không lỗi
        # if audio_info and audio_info.file_path:
        #     try:
        #         file_service.remove_local_file(audio_info.file_path)
        #     except Exception as e:
        #         print(f"⚠️ Lỗi khi xóa file local: {e}")
        print(f"🧹 Hoàn tất xử lý LessonGenerationRequestedEvent cho ai_job_id: {event.ai_job_id}")

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

