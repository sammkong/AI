#!/usr/bin/env python

import sys
import os
import json
import argparse
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import pika

from api.schemas import TrainingJobRequest

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin1234!@192.168.2.20:30672/")
APP2AI_EXCHANGE = "x.app2ai.direct"
TRAINING_QUEUE = "q.2ai.training"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def main():
    parser = argparse.ArgumentParser(description="training job publisher")
    parser.add_argument("--job-id", default="job_001")
    parser.add_argument("--dataset-version", default="v3")
    parser.add_argument("--requested-by", default="admin")
    args = parser.parse_args()

    payload = TrainingJobRequest(
        job_id=args.job_id,
        job_type="training",
        task_type="training",
        dataset_version=args.dataset_version,
        requested_by=args.requested_by,
        created_at=_utc_now(),
    )

    conn = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    ch = conn.channel()
    ch.basic_publish(
        exchange="",
        routing_key=TRAINING_QUEUE,
        body=json.dumps(payload.model_dump(), ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )
    conn.close()

    print(f"[OK] published -> {TRAINING_QUEUE}")
    print(json.dumps(payload.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
