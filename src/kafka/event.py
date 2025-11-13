# from pydantic import BaseModel, Field


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
