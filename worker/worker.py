import json
import logging
import os
import sys
import time

import pika

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
    stream=sys.stdout,
)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = os.getenv("QUEUE_NAME", "notifications")


def handle_email(message: dict) -> None:
    logging.info("[EMAIL] user=%s message=%s", message["user_id"], message["message"])


def handle_sms(message: dict) -> None:
    logging.info("[SMS] user=%s message=%s", message["user_id"], message["message"])


def handle_push(message: dict) -> None:
    logging.info("[PUSH] user=%s message=%s", message["user_id"], message["message"])


CHANNEL_HANDLERS = {
    "email": handle_email,
    "sms": handle_sms,
    "push": handle_push,
}


def process_notification(message: dict) -> None:
    if message.get("force_fail"):
        raise ValueError("Simulated processing error")

    channel_name = message.get("channel")
    handler = CHANNEL_HANDLERS.get(channel_name)
    if handler is None:
        raise ValueError(f"Unsupported notification channel: {channel_name}")

    handler(message)
    time.sleep(0.5)


def callback(channel, method, properties, body) -> None:
    try:
        message = json.loads(body)
        process_notification(message)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        # Reject invalid/failed messages without requeue so RabbitMQ routes them
        # through the configured DLX to notifications.dlq.
        logging.error("Processing error: %s; routing message to DLQ", exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as exc:
        # Unexpected/transient failures are retried by requeueing.
        logging.exception("Unexpected worker error: %s; requeueing", exc)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main() -> None:
    logging.info("Multi-channel worker started")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    channel.start_consuming()


if __name__ == "__main__":
    main()
