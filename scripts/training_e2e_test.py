#!/usr/bin/env python

import sys
import os
import json
import time
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin1234!@192.168.2.20:30672/")
APP2AI_EXCHANGE = "x.app2ai.direct"
TRAINING_IN = "q.2ai.training"
TRAINING_OUT = "q.2app.training"


def _connect():
    conn = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    ch = conn.channel()
    return conn, ch


def _publish(ch, payload: dict):
    ch.basic_publish(
        exchange=APP2AI_EXCHANGE,
        routing_key=TRAINING_IN,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )


def _poll(ch, queue: str, job_id: str, timeout: int = 30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        method, _, body = ch.basic_get(queue=queue, auto_ack=True)
        if body:
            msg = json.loads(body)
            if msg.get("job_id") == job_id:
                return msg
        time.sleep(0.5)
    return None


def main():
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    payload = {
        "job_id": job_id,
        "job_type": "training",
        "task_type": "training",
        "dataset_version": "v3",
        "requested_by": "admin",
        "created_at": "2026-04-12T00:00:00.000Z",
    }

    conn, ch = _connect()
    try:
        print(f"Publish -> {TRAINING_IN} job_id={job_id}")
        _publish(ch, payload)
        result = _poll(ch, TRAINING_OUT, job_id, timeout=30)
    finally:
        conn.close()

    if result is None:
        print("[FAIL] no completion event received")
        sys.exit(1)

    print("[PASS] completion event received")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
