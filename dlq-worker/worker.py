import json
import logging
import os
import sys

import pika

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
    stream=sys.stdout,
)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
DLQ_NAME = os.getenv("DLQ_NAME", "notifications.dlq")


def callback(channel, method, properties, body) -> None:
    try:
        message = json.loads(body)
        logging.error("[DLQ] Dead letter received: %s", message)
    except json.JSONDecodeError:
        logging.error("[DLQ] Non-JSON dead letter received: %r", body)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    logging.info("DLQ worker started")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=DLQ_NAME, on_message_callback=callback)
    channel.start_consuming()


if __name__ == "__main__":
    main()
