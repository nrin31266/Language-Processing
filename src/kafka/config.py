from confluent_kafka import Producer, Consumer

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_GROUP_ID = "inventory-service-group"


# src/kafka/config.py
def create_kafka_producer() -> Producer:
    producer_config = {
        "bootstrap.servers": "localhost:9092",
        "linger.ms": 5,  # Giảm latency
        "batch.num.messages": 100, # Tăng throughput
        "queue.buffering.max.ms": 50, # Tăng thời gian chờ để gom nhiều message hơn
    }
    return Producer(producer_config)

def create_kafka_consumer(topics: list[str]) -> Consumer:
    consumer_config = {
        "bootstrap.servers": "localhost:9092", 
        "group.id": "lp-service-group", 
        "auto.offset.reset": "earliest", # Đọc từ đầu nếu chưa có offset
        "enable.auto.commit": True, # Tự động commit offset
        "auto.commit.interval.ms": 1000, # Commit mỗi giây
    }
    consumer = Consumer(consumer_config)
    consumer.subscribe(topics)
    return consumer
