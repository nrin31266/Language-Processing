# src/kafka/consumer.py

import asyncio
import json
from typing import List

from confluent_kafka import KafkaError

from src import dto
from src.enum import LessonProcessingStep, LessonSourceType
from src.kafka.config import create_kafka_consumer
from src.kafka.event import (
    LessonGenerationRequestedEvent,
    LessonProcessingStepUpdatedEvent,
)
from src.kafka.producer import publish_lesson_processing_step_updated
from src.kafka.topic import (
    LESSON_GENERATION_REQUESTED_TOPIC,
)
from src.services import (
    media_service,
    ai_job_service,
    speech_to_text_service,
    batch_service,
)
from src.services.file_service import fetch_json_from_url, file_exists
from src.s3_storage import cloud_service
from src.utils.chunk_utils import chunk_list


async def handleLessonGenerationRequested(event: LessonGenerationRequestedEvent):
    """Xử lý khi có yêu cầu tạo bài học."""
    print(f"📥 Nhận LessonGenerationRequestedEvent: {event}")
    audio_info = None  # cho finally nếu sau này dọn file

    try:
        # Cho 2s cho hệ thống ổn định
        await asyncio.sleep(2)

        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return

        isSkip = False
        metadata: dto.AiMetadataDto

        # ───────────────────────────────────────────
        # 0. Lấy metadata ban đầu (nếu có)
        # ───────────────────────────────────────────
        try:
            fileMetadata = await fetch_json_from_url(event.ai_meta_data_url)
            if fileMetadata:
                metadata = dto.AiMetadataDto.model_validate(fileMetadata)
                print(f"✅ Fetched AI meta data from URL {event.ai_meta_data_url}")
            else:
                metadata = dto.AiMetadataDto()
        except Exception:
            metadata = dto.AiMetadataDto()  # Tạo object rỗng để tránh None

        uploadUrl = None
        metadataUploadUrl = event.ai_meta_data_url if event.ai_meta_data_url else None

        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return

        # ───────────────────────────────────────────
        # STEP 1: Download audio từ source_url
        # ───────────────────────────────────────────
        if metadata.sourceFetched is None or event.is_restart:
            print(f"🔍 Bắt đầu tải audio từ source_url cho Lesson id {event.lesson_id}")

            if event.source_type == LessonSourceType.youtube:
                audio_info = await media_service.download_youtube_audio(
                    dto.MediaAudioCreateRequest(input_url=event.source_url)
                )
            elif event.source_type == LessonSourceType.audio_file:
                audio_info = await media_service.download_audio_file(
                    dto.MediaAudioCreateRequest(input_url=event.source_url)
                )
            else:
                raise Exception(f"Unsupported LessonSourceType: {event.source_type}")

            if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
                print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
                return

            # Upload audio lên Cloudinary (async)
            uploadUrl = await cloud_service.upload_file(
                audio_info.file_path,
                public_id=f"lps/lessons/audio/{audio_info.sourceReferenceId}",
                resource_type="video",
            )

            audio_info.audioUrl = uploadUrl
            metadata.sourceFetched = dto.SourceFetchedDto.model_validate(
                audio_info.model_dump(by_alias=True)
            )

            # Upload metadata lên Cloudinary (async)
            metadataUploadUrl = await cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True), ensure_ascii=False),
                public_id=f"lps/lessons/{event.lesson_id}/ai-metadata",
            )
            print(
                f"✅ Đã tải audio cho Lesson với ai_job_id {event.ai_job_id}, "
                f"file tại: {audio_info.file_path}"
            )
        else:
            # Dùng lại metadata đã có
            audio_info = dto.AudioInfo.model_validate(metadata.sourceFetched)
            print(
                f"🔁 Sử dụng lại audio_info từ AI meta data cho Lesson với "
                f"ai_job_id {event.ai_job_id}: {audio_info}"
            )
            uploadUrl = audio_info.audioUrl
            isSkip = True
            metadataUploadUrl = event.ai_meta_data_url

            # Kiểm tra file audio local có tồn tại không, nếu không thì tải lại
            if not file_exists(audio_info.file_path):
                print(
                    f"⚠️ File audio local không tồn tại tại {audio_info.file_path}, "
                    f"sẽ tải lại từ audioUrl."
                )
                downloaded = await media_service.download_audio_file(
                    dto.MediaAudioCreateRequest(
                        input_url=audio_info.audioUrl,
                        audio_name=audio_info.sourceReferenceId,
                    )
                )
                audio_info.file_path = downloaded.file_path

        # ───────────────────────────────────────────
        # 1.1. Bổ sung duration nếu thiếu
        # ───────────────────────────────────────────
        if metadata.sourceFetched.duration is None:
            duration = await speech_to_text_service.get_audio_duration(audio_info.file_path)
            metadata.sourceFetched.duration = int(duration)
            print(
                f"🔍 Lấy duration cho audio tại {audio_info.file_path}. "
                f"Duration: {metadata.sourceFetched.duration}"
            )

        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return

        # Notify SOURCE_FETCHED
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
                durationSeconds=metadata.sourceFetched.duration
                if metadata.sourceFetched.duration
                else 0,
            )
        )
        isSkip = False
        print(
            f"✅ Đã gửi LessonProcessingStepUpdatedEvent SOURCE_FETCHED "
            f"cho Lesson với ai_job_id: {event.ai_job_id}"
        )

        # ───────────────────────────────────────────
        # STEP 2: Xử lý audio bằng AI (transcribe)
        # ───────────────────────────────────────────
        transcription_result: dto.TranscribedDto

        if metadata.transcribed is None or event.is_restart:
            print(f"🔍 Bắt đầu transcribe audio cho Lesson với ai_job_id: {event.ai_job_id}")

            raw_transcription = await speech_to_text_service.transcribe(audio_info.file_path)

            # raw_transcription có thể là dict, convert sang DTO
            metadata.transcribed = dto.TranscribedDto.model_validate(raw_transcription)
            transcription_result = metadata.transcribed

            print(f"✅ Audio transcribed for Lesson with ai_job_id: {event.ai_job_id}")

            # Cập nhật lại metadata lên cloud, trả về cùng đường dẫn cũ
            metadataUploadUrl = await cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True), ensure_ascii=False),
                public_id=f"lps/lessons/{event.lesson_id}/ai-metadata",
            )
            print(
                f"✅ Cập nhật AI meta data lên {metadataUploadUrl} "
                f"cho Lesson với ai_job_id: {event.ai_job_id}"
            )
        else:
            print(
                f"🔁 Sử dụng lại transcription từ AI meta data cho "
                f"Lesson với ai_job_id: {event.ai_job_id}"
            )
            isSkip = True
            transcription_result = metadata.transcribed

        if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
            print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng xử lý.")
            return

        # Notify TRANSCRIBED
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
        print(
            f"✅ Đã gửi LessonProcessingStepUpdatedEvent TRANSCRIBED "
            f"cho Lesson với ai_job_id: {event.ai_job_id}"
        )

        # ───────────────────────────────────────────
        # STEP 3: NLP analysis (chạy batch song song)
        # ───────────────────────────────────────────
        nlp_result: dto.NlpAnalyzedDto

        segments = transcription_result.segments
        sentences_payload = [
            {"orderIndex": idx, "text": seg.text} for idx, seg in enumerate(segments)
        ]

        batch_size = 10
        max_concurrency = 3  # muốn 3 batch song song

        if metadata.nlpAnalyzed is None or event.is_restart:
            print(
                f"🔍 Bắt đầu NLP analysis cho Lesson với ai_job_id: {event.ai_job_id}"
            )

            chunks = list(chunk_list(sentences_payload, batch_size))
            nlp_sentences: List[dto.SentenceAnalyzedDto] = []

            # chạy từng "wave", mỗi wave tối đa 3 chunk
            for i in range(0, len(chunks), max_concurrency):
                if await ai_job_service.aiJobWasCancelled(event.ai_job_id):
                    print(f"⚠️ AI Job {event.ai_job_id} đã bị hủy, dừng NLP.")
                    return

                wave = chunks[i : i + max_concurrency]

                print(
                    f"🧠 NLP wave {i // max_concurrency + 1}: "
                    f"{wave[0][0]['orderIndex']} → {wave[-1][-1]['orderIndex']} running..."
                )

                # tạo tasks cho từng chunk trong wave
                tasks = [
                    batch_service.analyze_sentence_batch(chunk)
                    for chunk in wave
                ]

                wave_results = await asyncio.gather(*tasks, return_exceptions=True)

                for chunk, result in zip(wave, wave_results):
                    if isinstance(result, Exception):
                        # tuỳ bạn xử lý: raise luôn hay log + skip
                        print(f"⚠️ Lỗi NLP batch {chunk[0]['orderIndex']} → {chunk[-1]['orderIndex']}: {result}")
                        raise result

                    for item in result:
                        nlp_sentences.append(dto.SentenceAnalyzedDto(**item))

            # sắp xếp lại cho chắc (nếu sau này cần guarantee order)
            nlp_sentences.sort(key=lambda s: s.orderIndex)

            nlp_result = dto.NlpAnalyzedDto(sentences=nlp_sentences)

            # Lưu vào metadata
            metadata.nlpAnalyzed = dto.NlpAnalyzedDto.model_validate(
                nlp_result.model_dump()
            )

            metadataUploadUrl = await cloud_service.upload_json_content(
                json.dumps(metadata.model_dump(by_alias=True), ensure_ascii=False),
                public_id=f"lps/lessons/{event.lesson_id}/ai-metadata",
            )

            print(
                f"✅ NLP analysis hoàn thành và đã upload metadata lên {metadataUploadUrl}"
            )

            await publish_lesson_processing_step_updated(
                LessonProcessingStepUpdatedEvent(
                    aiJobId=event.ai_job_id,
                    processingStep=LessonProcessingStep.NLP_ANALYZED,
                    aiMessage="NLP analysis completed successfully.",
                    aiMetadataUrl=metadataUploadUrl,
                    isSkip=False,
                )
            )
        else:
            print(
                f"🔁 Sử dụng lại NLP metadata cho ai_job_id: {event.ai_job_id}"
            )
            nlp_result = dto.NlpAnalyzedDto.model_validate(metadata.nlpAnalyzed)

            await publish_lesson_processing_step_updated(
                LessonProcessingStepUpdatedEvent(
                    aiJobId=event.ai_job_id,
                    processingStep=LessonProcessingStep.NLP_ANALYZED,
                    aiMessage="NLP reused from previous metadata.",
                    aiMetadataUrl=event.ai_meta_data_url,
                    isSkip=True,
                )
            )

        print(
            f"✅ Đã gửi LessonProcessingStepUpdatedEvent NLP_ANALYZED "
            f"cho Lesson với ai_job_id: {event.ai_job_id}"
        )

        # Cho 2s cho hệ thống ổn định, sau đó gửi COMPLETED
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
                isSkip=False,
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
        # Nếu sau này muốn dọn file local thì mở lại đoạn này
        # if audio_info and audio_info.file_path:
        #     try:
        #         file_service.remove_local_file(audio_info.file_path)
        #     except Exception as e:
        #         print(f"⚠️ Lỗi khi xóa file local: {e}")
        print(
            f"🧹 Hoàn tất xử lý LessonGenerationRequestedEvent cho ai_job_id: {event.ai_job_id}"
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
            msg = await asyncio.to_thread(consumer.poll, 0.1)  # 100ms timeout

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Kafka error: {msg.error()}")
                continue

            topic = msg.topic()

            try:
                payload = json.loads(msg.value().decode("utf-8"))

                if topic == LESSON_GENERATION_REQUESTED_TOPIC:
                    event = LessonGenerationRequestedEvent(**payload)
                    asyncio.create_task(handleLessonGenerationRequested(event))

            except Exception as e:
                print(f"⚠️ Lỗi xử lý message (topic: {topic}): {e}")

    except asyncio.CancelledError:
        print("📪 Đang dừng consumer...")
    finally:
        await asyncio.to_thread(consumer.close)
        print("📪 Consumer đã dừng.")


async def start_kafka_consumers():
    """
    Hàm này được gọi bởi `lifespan` trong `main.py`
    """
    await consume_events()
