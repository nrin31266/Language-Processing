# src/kafka/consumer.py

import asyncio
import json
from src.kafka.config import create_kafka_consumer
# from src.kafka.event import (
#     InventoryFailedEvent,
#     InventoryReservedEvent,
#     OrderCreatedEvent,
#     OrderCancelledEvent,
# )
# from src.kafka.producer import publish_inventory_reserved, publish_inventory_failed
# from src.database import SessionLocal
# from src.repositories import product_repository, reserved_order_repository
from confluent_kafka import KafkaError

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

async def consume_events():
    """
    Một consumer duy nhất lắng nghe TẤT CẢ các topic nghiệp vụ.
    """
    topics = ["orders", "orders_cancelled"]
    
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

                # # Phân luồng nghiệp vụ dựa trên topic
                # if topic == "orders":
                #     event = OrderCreatedEvent(**payload)
                #     # "Bắn" task đi xử lý và không chờ, có cổng Semaphore bảo vệ
                #     asyncio.create_task(
                #         run_handler_with_limit(handle_order_created_event, event)
                #     )

                # elif topic == "orders_cancelled":
                #     event = OrderCancelledEvent(**payload)
                #     # "Bắn" task đi xử lý và không chờ, có cổng Semaphore bảo vệ
                #     asyncio.create_task(
                #         run_handler_with_limit(handle_order_cancelled_event, event)
                #     )

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
# ============================================
# import asyncio
# import json
# from src.kafka.config import create_kafka_consumer
# from src.event import (
#     InventoryFailedEvent,
#     InventoryReservedEvent,
#     OrderCreatedEvent,
#     OrderCancelledEvent,
# )
# from src.kafka.producer import publish_inventory_reserved, publish_inventory_failed
# from sqlalchemy.orm import Session
# from fastapi import Depends
# from src.database import get_db
# from src.repositories import product_repository, reserved_order_repository

# from src.database import SessionLocal
# from confluent_kafka import KafkaError

# async def handle_order_created_event(
#     event: OrderCreatedEvent
# ):
#     db = SessionLocal()
#     print(f"📥 Nhận OrderCreatedEvent: {event}")
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
#             # Đừng flush ở đây - sẽ gây blocking
#             await publish_inventory_reserved(
#                 InventoryReservedEvent(
#                     order_id=event.order_id,
#                     status="RESERVED",
#                     message="Hàng đã được giữ thành công.",
#                 )
#             )
#         else:
#             await publish_inventory_failed(
#                 InventoryFailedEvent(
#                     order_id=event.order_id, 
#                     status="FAILED", 
#                     message="Không đủ hàng trong kho."
#                 )
#             )
#     except Exception as e:
#         print(f"❌ Giữ hàng thất bại: {e}")
#         await publish_inventory_failed(
#             InventoryFailedEvent(
#                 order_id=event.order_id, status="FAILED", message=str(e)
#             )
#         )
#     finally:
#         db.close()


# async def handle_order_cancelled_event(
#     event: OrderCancelledEvent
# ):
#     db = SessionLocal()
#     print(f"📥 Nhận OrderCancelledEvent: {event}")
#     reserved_order = reserved_order_repository.get_by_order_id_and_product_id(
#         db, event.order_id, event.product_id
#     )
#     if reserved_order:
#         # Hoàn trả hàng
#         product_repository.increase_stock(db, event.product_id, reserved_order.quantity)
#         reserved_order_repository.delete_reserved_order(db, event.order_id, event.product_id)
#         print(f"✅ Đã hoàn trả hàng cho Order {event.order_id}")
#     db.close()

# async def consume_orders():
#     consumer = await asyncio.to_thread(create_kafka_consumer, ["orders"])
#     try:
#         while True:
#             # Poll với timeout ngắn
#             msg = await asyncio.to_thread(consumer.poll, 0.1) # 100ms timeout
#             if msg is None:
#                 # Bạn không cần sleep nữa, vì poll đã "chờ" 0.1s rồi
#                 continue
#             if msg.error():
#                 if msg.error().code() == KafkaError._PARTITION_EOF:
#                     continue
#                 print(f"Kafka error: {msg.error()}")
#                 continue
            
#             try:
#                 payload = json.loads(msg.value().decode("utf-8"))
#                 event = OrderCreatedEvent(**payload)
#                 # Chạy handler trong background, 
#                 # create_task để xử lý, không await ở đây
#                 asyncio.create_task(handle_order_created_event(event))
#             except Exception as e:
#                 print(f"⚠️ Error processing orders message: {e}")
#     except asyncio.CancelledError:
#         print("📪 Stopping orders consumer")
#     finally:
#         # 3. Chạy hàm blocking close trong thread
#         await asyncio.to_thread(consumer.close)

# async def consume_orders_cancelled():
#     consumer = await asyncio.to_thread(create_kafka_consumer, ["orders_cancelled"])
#     try:
#         while True:
#             msg = await asyncio.to_thread(consumer.poll, 0.1)
#             if msg is None:
#                 continue
#             if msg.error():
#                 if msg.error().code() == KafkaError._PARTITION_EOF:
#                     continue
#                 print(f"Kafka error: {msg.error()}")
#                 continue
            
#             try:
#                 payload = json.loads(msg.value().decode("utf-8"))
#                 event = OrderCancelledEvent(**payload)
#                 # Chạy handler trong background
#                  # create_task để xử lý, không await ở đây
#                 asyncio.create_task(handle_order_cancelled_event(event))
#             except Exception as e:
#                 print(f"⚠️ Error processing cancelled orders message: {e}")
#     except asyncio.CancelledError:
#         print("📪 Stopping cancelled orders consumer")
#     finally:
#         await asyncio.to_thread(consumer.close)

# async def start_kafka_consumers():
#     print("🚀 Starting Kafka consumers...")
#     # Chạy consumers trong background
#     await asyncio.gather(
#         consume_orders(),
#         consume_orders_cancelled(),
#         return_exceptions=True
#     )


#  =============================================
# async def start_kafka_consumers():
#     consumer_orders = create_kafka_consumer(["orders"])
#     consumer_cancelled = create_kafka_consumer(["orders_cancelled"])

    

#     async def poll_consumer(consumer, handler, model_cls):
#         while True:
#             msg = consumer.poll(1.0)
#             if msg is None:
#                 await asyncio.sleep(0.1)
#                 continue
#             if msg.error():
#                 print(f"Kafka error: {msg.error()}")
#                 continue
#             try:
#                 payload = json.loads(msg.value().decode("utf-8"))
#                 event = model_cls(**payload)
#                 db = SessionLocal()
#                 try:
#                     await handler(event, db=db)
#                 finally:
#                     db.close()
#             except Exception as e:
#                 print(f"⚠️ Error processing message: {e}")


#     await asyncio.gather(
#         poll_consumer(consumer_orders, handle_order_created_event, OrderCreatedEvent),
#         poll_consumer(
#             consumer_cancelled, handle_order_cancelled_event, OrderCancelledEvent
#         ),
#     )
