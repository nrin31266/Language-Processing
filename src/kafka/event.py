from pydantic import BaseModel, Field
from typing import Optional

from src.enum import LessonSourceType, LessonProcessingStep
class LessonGenerationRequestedEvent(BaseModel):
    source_type: LessonSourceType = Field(..., alias="sourceType")
    source_url: Optional[str] = Field(None, alias="sourceUrl")
    ai_job_id: Optional[str] = Field(None, alias="aiJobId")

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

    class Config:
        from_attributes = True
        populate_by_name = True
# # public class OrderCancelledEvent {
# #     private Long orderId;
# #     private Long userId;
# #     private String productId;
# #     private int quantity;
# #     private String reason;
# # }
# # consumer
# class OrderCancelledEvent(BaseModel):
#     order_id: int = Field(..., alias="orderId")
#     user_id: int = Field(..., alias="userId")
#     product_id: str = Field(..., alias="productId")
#     quantity: int = Field(..., alias="quantity")
#     reason: str = Field(..., alias="reason")

#     class Config:
#         from_attributes = True
#         populate_by_name = True


# class OrderCreatedEvent(BaseModel):
#     order_id: int = Field(..., alias="orderId")
#     user_id: int = Field(..., alias="userId")
#     product_id: str = Field(..., alias="productId")
#     quantity: int = Field(..., alias="quantity")
#     total: float = Field(..., alias="total")

#     class Config:
#         from_attributes = True
#         populate_by_name = True


# # producer do not change


# class InventoryReservedEvent(BaseModel):
#     order_id: int = Field(..., alias="orderId")
#     status: str
#     message: str

#     class Config:
#         from_attributes = True
#         populate_by_name = True


# class InventoryFailedEvent(BaseModel):
#     order_id: int = Field(..., alias="orderId") 
#     status: str
#     message: str

#     class Config:
#         from_attributes = True
#         populate_by_name = True
