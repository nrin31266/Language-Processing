
import asyncio
import json
from typing import List

from src import dto
from src.enum import LessonProcessingStep, LessonSourceType
from src.kafka.event import (
    LessonGenerationRequestedEvent,
    LessonProcessingStepUpdatedEvent,
)
from src.kafka.producer import publish_lesson_processing_step_updated
from src.services import (
    media_service,
    ai_job_service,
    speech_to_text_service,
    batch_service,
)
from src.services.file_service import fetch_json_from_url, file_exists
from src.s3_storage import cloud_service
from src.utils.chunk_utils import chunk_list


# Helper functions
async def _is_cancelled(ai_job_id: str | None) -> bool:
    r = False
    if not ai_job_id:
        r = False
    else:
        r = await ai_job_service.ai_job_was_cancelled(ai_job_id)
    if r:
        print(f"lesson_generation_cancelled ai_job_id={ai_job_id}")
    return r


async def _load_metadata(url: str | None) -> dto.LessonGenerationAiMetadataDto:
    if not url:
        return dto.LessonGenerationAiMetadataDto()
    try:
        data = await fetch_json_from_url(url)
        return dto.LessonGenerationAiMetadataDto.model_validate(data) if data else dto.LessonGenerationAiMetadataDto()
    except Exception:
        return dto.LessonGenerationAiMetadataDto()


async def _save_metadata(lesson_id: int | None, metadata: dto.LessonGenerationAiMetadataDto) -> str | None:
    if lesson_id is None:
        return None
    return await cloud_service.upload_json_content(
        json.dumps(metadata.model_dump(by_alias=True), ensure_ascii=False),
        public_id=f"lps/lessons/{lesson_id}/ai-metadata",
    )


async def _publish_step(
    *,
    ai_job_id: str | None,
    step: LessonProcessingStep,
    message: str,
    audio_url: str | None = None,
    source_reference_id: str | None = None,
    thumbnail_url: str | None = None,
    is_skip: bool = False,
    metadata_url: str | None = None,
    duration_seconds: int = 0,
) -> None:
    await publish_lesson_processing_step_updated(
        LessonProcessingStepUpdatedEvent(
            aiJobId=ai_job_id,
            processingStep=step,
            audioUrl=audio_url,
            sourceReferenceId=source_reference_id,
            thumbnailUrl=thumbnail_url,
            isSkip=is_skip,
            aiMetadataUrl=metadata_url,
            durationSeconds=duration_seconds,
            aiMessage=message,
        )
    )
    print(f">[Lesson Generation] Step {step} published for ai_job_id={ai_job_id}: {message}")


async def _download_audio_by_source(event: LessonGenerationRequestedEvent) -> dto.AudioInfo:
    if event.source_type == LessonSourceType.youtube:
        return await media_service.download_youtube_audio(
            dto.MediaAudioCreateRequest(input_url=event.source_url)
        )
    if event.source_type == LessonSourceType.audio_file:
        return await media_service.download_audio_file(
            dto.MediaAudioCreateRequest(input_url=event.source_url)
        )
    raise Exception(f"Unsupported LessonSourceType: {event.source_type}")


async def _ensure_local_audio_file(audio_info: dto.AudioInfo) -> dto.AudioInfo:
    if file_exists(audio_info.file_path):
        print(f"Audio file already exists locally: {audio_info.file_path}")
        return audio_info

    downloaded = await media_service.download_audio_file(
        dto.MediaAudioCreateRequest(
            input_url=audio_info.audioUrl,
            audio_name=audio_info.sourceReferenceId,
        )
    )
    audio_info.file_path = downloaded.file_path
    print(f"Downloaded audio file locally: {audio_info.file_path}")
    return audio_info

async def handle_lesson_generation_requested(event: LessonGenerationRequestedEvent) -> None:
    print(f"[Lesson Generation] Started for ai_job_id={event.ai_job_id}")
    audio_info: dto.AudioInfo | None = None

    try:
        await asyncio.sleep(2)

        if await _is_cancelled(event.ai_job_id):
            return

        is_skip = False
        metadata = await _load_metadata(event.ai_meta_data_url)
        metadata_url: str | None = event.ai_meta_data_url or None
        audio_url: str | None = None

        if await _is_cancelled(event.ai_job_id):
            return

        # STEP 1: source audio
        if metadata.sourceFetched is None or event.is_restart:
            audio_info = await _download_audio_by_source(event)

            if await _is_cancelled(event.ai_job_id):
                return

            audio_url = await cloud_service.upload_file(
                audio_info.file_path,
                public_id=f"lps/lessons/audio/{audio_info.sourceReferenceId}",
                resource_type="video",
            )

            audio_info.audioUrl = audio_url
            metadata.sourceFetched = dto.SourceFetchedDto.model_validate(
                audio_info.model_dump(by_alias=True)
            )

            metadata_url = await _save_metadata(event.lesson_id, metadata)
        else:
            audio_info = dto.AudioInfo.model_validate(metadata.sourceFetched)
            audio_url = audio_info.audioUrl
            metadata_url = event.ai_meta_data_url
            is_skip = True

            audio_info = await _ensure_local_audio_file(audio_info)

        if metadata.sourceFetched and metadata.sourceFetched.duration is None:
            duration = await speech_to_text_service.get_audio_duration(audio_info.file_path)
            metadata.sourceFetched.duration = int(duration)

        if await _is_cancelled(event.ai_job_id):
            return

        await _publish_step(
            ai_job_id=event.ai_job_id,
            step=LessonProcessingStep.SOURCE_FETCHED,
            message="Audio source fetched successfully.",
            audio_url=audio_url,
            source_reference_id=audio_info.sourceReferenceId,
            thumbnail_url=audio_info.thumbnailUrl,
            is_skip=is_skip,
            metadata_url=metadata_url,
            duration_seconds=int(metadata.sourceFetched.duration or 0)
            if metadata.sourceFetched
            else 0,
        )
        
        print(f"✅ [Lesson Generation] Step SOURCE_FETCHED completed for ai_job_id={event.ai_job_id}")
        
        is_skip = False

        # STEP 2: transcribe
        if metadata.transcribed is None or event.is_restart:
            raw = await speech_to_text_service.transcribe(audio_info.file_path)
            metadata.transcribed = dto.TranscribedDto.model_validate(raw)
            metadata_url = await _save_metadata(event.lesson_id, metadata)
        else:
            is_skip = True

        if await _is_cancelled(event.ai_job_id):
            return

        await _publish_step(
            ai_job_id=event.ai_job_id,
            step=LessonProcessingStep.TRANSCRIBED,
            message="Audio transcribed successfully.",
            audio_url=audio_url,
            is_skip=is_skip,
            metadata_url=metadata_url,
        )
        print(f"✅ [Lesson Generation] Step TRANSCRIBED completed for ai_job_id={event.ai_job_id}")
        is_skip = False

        # STEP 3: NLP
        transcription_result: dto.TranscribedDto = metadata.transcribed
        segments = transcription_result.segments
        sentences_payload = [{"orderIndex": i, "text": seg.text} for i, seg in enumerate(segments)]

        batch_size = 10
        max_concurrency = 3

        if metadata.nlpAnalyzed is None or event.is_restart:
            chunks = list(chunk_list(sentences_payload, batch_size))
            analyzed: List[dto.SentenceAnalyzedDto] = []

            for i in range(0, len(chunks), max_concurrency):
                print(f"[Lesson Generation] NLP analyzing sentences {i*batch_size} to {(i + max_concurrency)*batch_size} for ai_job_id={event.ai_job_id}")
                
                if await _is_cancelled(event.ai_job_id):
                    return

                wave = chunks[i : i + max_concurrency]
                tasks = [batch_service.analyze_sentence_batch(chunk) for chunk in wave]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for chunk, result in zip(wave, results):
                    if isinstance(result, Exception):
                        raise result
                    for item in result:
                        analyzed.append(dto.SentenceAnalyzedDto(**item))

            analyzed.sort(key=lambda s: s.orderIndex)
            metadata.nlpAnalyzed = dto.NlpAnalyzedDto(sentences=analyzed)
            metadata_url = await _save_metadata(event.lesson_id, metadata)

            await _publish_step(
                ai_job_id=event.ai_job_id,
                step=LessonProcessingStep.NLP_ANALYZED,
                message="NLP analysis completed successfully.",
                metadata_url=metadata_url,
                is_skip=False,
            )
        else:
            await _publish_step(
                ai_job_id=event.ai_job_id,
                step=LessonProcessingStep.NLP_ANALYZED,
                message="NLP reused from previous metadata.",
                metadata_url=event.ai_meta_data_url,
                is_skip=True,
            )

        print(f"✅ [Lesson Generation] Step NLP_ANALYZED completed for ai_job_id={event.ai_job_id}")
        
        await asyncio.sleep(2)
        if await _is_cancelled(event.ai_job_id):
            return

        await _publish_step(
            ai_job_id=event.ai_job_id,
            step=LessonProcessingStep.COMPLETED,
            message="Lesson generation completed successfully.",
            metadata_url=metadata_url,
            is_skip=False,
        )

    except Exception as e:
        print(f"lesson_generation_failed ai_job_id={event.ai_job_id} err={e}")
        await publish_lesson_processing_step_updated(
            LessonProcessingStepUpdatedEvent(
                aiMessage=f"Lesson generation failed: {e}",
                processingStep=LessonProcessingStep.FAILED,
                aiJobId=event.ai_job_id,
            )
        )
    finally:
        print(f"lesson_generation_done ai_job_id={event.ai_job_id}")
        
