# ============================================================
# RabbitMQ publisher — AI → App
#
# Exchange : x.ai2app.direct
# Routing  : routing_key == queue name (direct exchange)
# ============================================================

import json
import os
import pika

from messaging.structured_log import get_logger

RABBITMQ_URL    = os.getenv("RABBITMQ_URL", "amqp://admin:admin1234!@192.168.2.20:30672/")
AI2APP_EXCHANGE = "x.ai2app.direct"

_PROPS = pika.BasicProperties(
    content_type="application/json",
    delivery_mode=2,        # persistent
)

log = get_logger("publisher")


def publish(channel: pika.channel.Channel, routing_key: str, message: dict) -> None:
    """
    기존 channel 을 사용해 메시지를 publish.
    consumer callback 내부에서 호출.
    """
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    channel.basic_publish(
        exchange=AI2APP_EXCHANGE,
        routing_key=routing_key,
        body=body,
        properties=_PROPS,
    )
    log.info("published",
             routing_key=routing_key,
             outbox_id=message.get("outbox_id", "(unknown)"),
             email_id=message.get("email_id", "(unknown)"),
             status=message.get("status", "ok"))


class StandalonePublisher:
    """독립 연결이 필요한 경우 (E2E 테스트, 배치) 사용하는 컨텍스트 매니저."""

    def __init__(self, url: str = RABBITMQ_URL):
        self._url  = url
        self._conn = None
        self._ch   = None

    def __enter__(self) -> "StandalonePublisher":
        params     = pika.URLParameters(self._url)
        self._conn = pika.BlockingConnection(params)
        self._ch   = self._conn.channel()
        return self

    def publish(self, routing_key: str, message: dict) -> None:
        publish(self._ch, routing_key, message)

    def __exit__(self, *_) -> None:
        if self._conn and not self._conn.is_closed:
            self._conn.close()
