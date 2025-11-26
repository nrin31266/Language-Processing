import json
from src.kafka.config import create_kafka_producer

from src.kafka.config import create_kafka_producer
from src.kafka.event import LessonProcessingStepUpdatedEvent
from src.kafka.topic import LESSON_PROCESSING_STEP_UPDATED_TOPIC
import asyncio

producer = create_kafka_producer()
async def publish_lesson_processing_step_updated(event: LessonProcessingStepUpdatedEvent) -> None:
    try:
        producer.produce(
            topic=LESSON_PROCESSING_STEP_UPDATED_TOPIC,
            key=str(event.ai_job_id),
            value=event.model_dump_json(by_alias=True),
        )
        # Poll để trigger delivery callbacks
        await asyncio.to_thread(producer.poll, 0)
    except Exception as e:
        print(f"❌ Failed to send LessonProcessingStepUpdatedEvent: {e}")
# # def _delivery_report(err, msg):
# #     """Callback cho kết quả gửi message"""
# #     if err is not None:
# #         print(f"❌ Message delivery failed: {err}")
# #     else:
# #         print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}]")

# async def publish_inventory_reserved(event: InventoryReservedEvent) -> None:
#     try:
#         producer.produce(
#             topic=TOPIC_INVENTORY_RESERVED,
#             key=str(event.order_id),
#             value=event.model_dump_json(by_alias=True),
#         )
#         # CHỈ poll để trigger delivery callbacks, không flush
#         await asyncio.to_thread(producer.poll, 0)
#         print(f"✅ Sent InventoryReservedEvent for Order {event.order_id}")
#     except Exception as e:
#         print(f"❌ Failed to send InventoryReservedEvent: {e}")


# async def publish_inventory_failed(event: InventoryFailedEvent):
#     try:
#         producer.produce(
#             topic=TOPIC_INVENTORY_FAILED,
#             key=str(event.order_id),
#             value=event.model_dump_json(by_alias=True),
#         )
#         await asyncio.to_thread(producer.poll, 0)
#         print(f"📤 Queued InventoryFailedEvent for Order {event.order_id}")
#     except Exception as e:
#         print(f"❌ Failed to send InventoryFailedEvent: {e}")

# Background task để flush messages định kỳ
async def periodic_flush():
    while True:
        await asyncio.sleep(1)  # Chạy mỗi giây
        # Flush trong thread để tránh blocking event loop
        await asyncio.to_thread(producer.flush, 0.1)  # Timeout ngắn