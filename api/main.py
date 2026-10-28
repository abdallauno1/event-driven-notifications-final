import json
import os
from contextlib import closing
from typing import Literal

import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME = os.getenv("QUEUE_NAME", "notifications")

app = FastAPI(title="Event-Driven Notification API", version="1.0.0")


class Notification(BaseModel):
    user_id: str = Field(min_length=1)
    channel: Literal["email", "sms", "push"]
    message: str = Field(min_length=1)
    force_fail: bool = False


def rabbitmq_connection() -> pika.BlockingConnection:
    return pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
    )


def publish_notification(notification: Notification) -> None:
    # The queue topology is provisioned by rabbitmq-definitions.json.
    # Do not redeclare it here without the same TTL/DLX arguments.
    with closing(rabbitmq_connection()) as connection:
        channel = connection.channel()
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(notification.model_dump()),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
            mandatory=True,
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/notifications", status_code=202)
def create_notification(notification: Notification):
    try:
        publish_notification(notification)
    except (pika.exceptions.AMQPError, pika.exceptions.UnroutableError) as exc:
        raise HTTPException(status_code=503, detail="RabbitMQ is unavailable") from exc
    return {"status": "queued", "notification": notification}
