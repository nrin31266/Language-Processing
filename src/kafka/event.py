# src/kafka/event.py
from pydantic import BaseModel, Field
from typing import Optional

from src.enum import LessonSourceType, LessonProcessingStep
class LessonGenerationRequestedEvent(BaseModel):
    source_type: LessonSourceType = Field(..., alias="sourceType")
    source_url: Optional[str] = Field(None, alias="sourceUrl")
    ai_job_id: Optional[str] = Field(None, alias="aiJobId")
    lesson_id: Optional[int] = Field(None, alias="lessonId")
    ai_meta_data_url: Optional[str] = Field(None, alias="aiMetadataUrl")
    is_restart: Optional[bool] = Field(False, alias="isRestart")

    class Config:
        from_attributes = True
        populate_by_name = True


class LessonProcessingStepUpdatedEvent(BaseModel):
    processing_step: LessonProcessingStep = Field(..., alias="processingStep")
    ai_message: Optional[str] = Field(None, alias="aiMessage")
    ai_job_id: Optional[str] = Field(None, alias="aiJobId")
    audio_url: Optional[str] = Field(None, alias="audioUrl")
    source_reference_id: Optional[str] = Field(None, alias="sourceReferenceId")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    is_skip: Optional[bool] = Field(None, alias="isSkip")
    ai_meta_data_url: Optional[str] = Field(None, alias="aiMetadataUrl")
    duration_seconds: Optional[int] = Field(None, alias="durationSeconds")

    class Config:
        from_attributes = True
        populate_by_name = True
        validate_assignment = True

class PhoneticsDto(BaseModel):
    us: str = ""
    uk: str = ""
    audio_us: Optional[str] = Field(None, alias="audioUs")
    audio_uk: Optional[str] = Field(None, alias="audioUk")

    class Config:
        from_attributes = True
class DefinitionDto(BaseModel):
    type: str = ""
    definition: str = ""
    vietnamese: str = ""
    example: str = ""

    class Config:
        from_attributes = True

class WordAnalyzedEvent(BaseModel):
    word: str
    display_word: str = Field("", alias="displayWord")
    is_valid_word: bool = Field(True, alias="isValidWord")
    word_type: str = Field("normal", alias="wordType")
    cefr_level: str = Field("unknown", alias="cefrLevel")
    phonetics: Optional[PhoneticsDto] = None
    definitions: Optional[list[DefinitionDto]] = None

    class Config:
        from_attributes = True
class WordQueueHandlerEvent(BaseModel):
    # 1 field for processing word, 1 field for status later
    word: str
    class Config:
        from_attributes = True