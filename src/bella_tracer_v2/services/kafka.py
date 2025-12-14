import os
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


async def retrieve_aio_kafka_consumer(
    topic: str, consumer_group: str = "q1"
) -> AIOKafkaConsumer:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",
        group_id=consumer_group,
    )
    return consumer


async def retrieve_aio_kafka_producer() -> AIOKafkaProducer:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

    producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
    return producer


__all__ = ["retrieve_aio_kafka_consumer", "retrieve_aio_kafka_producer"]
