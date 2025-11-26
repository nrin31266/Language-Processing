from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel  # 👈 THÊM DÒNG NÀY
from datetime import datetime as DateTime
from src.enum   import LessonProcessingStep
T = TypeVar("T")


class ApiResponse(GenericModel, Generic[T]):  # → GenericModel
    """
    Một lớp response chung cho API.
    """

    code: int = Field(default=200, description="Mã code ứng dụng")
    message: Optional[str] = Field(default="Success", description="Thông điệp kết quả")
    result: Optional[T] = Field(default=None, description="Dữ liệu trả về")

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "Success"):
        """Factory method tương tự trong Java"""
        return cls(code=200, message=message, result=data)

    @classmethod
    def error(cls, code: int, message: str):
        """Factory method cho lỗi chung"""
        return cls(code=code, message=message)


class MediaAudioCreateRequest(BaseModel):
    input_url: str
    
class AudioInfo(BaseModel):
    file_path: str
    duration: Optional[int] = None  # duration in seconds
    sourceReferenceId: Optional[str] = Field(None, alias="sourceReferenceId")
    thumbnailUrl: Optional[str] = Field(None, alias="thumbnailUrl")
    audioUrl: Optional[str] = Field(None, alias="audioUrl")
    class Config:
        from_attributes = True

class AIJobResponse(BaseModel):
    id: str
    user_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
# class LessonProcessingStep(str, Enum):
#     NONE = "NONE"
#     PROCESSING_STARTED = "PROCESSING_STARTED"
#     SOURCE_FETCHED = "SOURCE_FETCHED"
#     TRANSCRIBED = "TRANSCRIBED"
#     NLP_ANALYZED = "NLP_ANALYZED"
#     COMPLETED = "COMPLETED"
#     FAILED = "FAILED"

class AiMetadataDto(BaseModel):
    source_fetched: Optional[Any] = None
    transcription_started: Optional[Any] = None
    nlp_analysis_started: Optional[Any] = None

    class Config:
        from_attributes = True


# class BlogResponse(BaseModel):
#     id: int
#     title: str
#     content: str
#     published: bool
#     user_id: str

#     creator: "User"
#     class Config:
#         from_attributes = True

# class Blog(BaseModel):
#     title: str
#     content: str
#     published: bool = True
#     user_id: str
#     class Config:
#         from_attributes = True

# class User(BaseModel):
#     keycloak_id: str
#     email: str
#     first_name: str
#     last_name: str

#     class Config:
#         from_attributes = True

# class BlogCreateRequest(BaseModel):
#     title: str
#     content: str
#     published: bool = True

# class UserResponse(BaseModel):
#     keycloak_id: str
#     email: str
#     first_name: str
#     last_name: str
#     blogs : "List[Blog]"

#     class Config:
#         from_attributes = True


# class LoginRequest(BaseModel):
#     email: str
#     password: str
