#!/usr/bin/env python
# ============================================================
# RabbitMQ End-to-End 테스트 스크립트
#
# 전제 조건
# ----------
# 1. RabbitMQ 실행 중 (기본 amqp://guest:guest@localhost:5672/)
# 2. consumer_classify.py 실행 중
# 3. consumer_draft.py 실행 중
#
# 실행
# ----
#   python scripts/e2e_test.py
#   RABBITMQ_URL=amqp://user:pass@host:5672/ python scripts/e2e_test.py
#
# 옵션
# ----
#   --timeout 30     응답 대기 최대 초 (기본 30)
#   --classify-only  classify 만 테스트
#   --draft-only     draft 만 테스트
# ============================================================

import sys
import os
import json
import time
import uuid
import argparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import pika

RABBITMQ_URL    = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
APP2AI_EXCHANGE = "x.app2ai.direct"
AI2APP_EXCHANGE = "x.ai2app.direct"

CLASSIFY_IN  = "q.2ai.classify"
CLASSIFY_OUT = "q.2app.classify"
DRAFT_IN     = "q.2ai.draft"
DRAFT_OUT    = "q.2app.draft"

_PROPS = pika.BasicProperties(
    content_type="application/json",
    delivery_mode=2,
)


# ── 헬퍼 ─────────────────────────────────────────────────────

def _connect() -> tuple:
    conn = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    ch   = conn.channel()
    return conn, ch


def _declare(ch):
    for ex, etype in [(APP2AI_EXCHANGE, "direct"), (AI2APP_EXCHANGE, "direct")]:
        ch.exchange_declare(exchange=ex, exchange_type=etype, durable=True)
    for q in [CLASSIFY_IN, CLASSIFY_OUT, DRAFT_IN, DRAFT_OUT]:
        ch.queue_declare(queue=q, durable=True)
    ch.queue_bind(CLASSIFY_IN,  APP2AI_EXCHANGE, CLASSIFY_IN)
    ch.queue_bind(CLASSIFY_OUT, AI2APP_EXCHANGE, CLASSIFY_OUT)
    ch.queue_bind(DRAFT_IN,     APP2AI_EXCHANGE, DRAFT_IN)
    ch.queue_bind(DRAFT_OUT,    AI2APP_EXCHANGE, DRAFT_OUT)


def _publish(ch, exchange: str, routing_key: str, message: dict):
    ch.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(message, ensure_ascii=False).encode(),
        properties=_PROPS,
    )


def _poll(ch, queue: str, request_id: str, timeout: int) -> dict | None:
    """
    지정 큐를 polling 하여 request_id 가 일치하는 메시지 반환.
    timeout 초 안에 없으면 None.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        method, _, body = ch.basic_get(queue=queue, auto_ack=True)
        if body:
            msg = json.loads(body)
            if msg.get("request_id") == request_id:
                return msg
            # 다른 request_id → 다시 큐에 넣지 않고 버림 (E2E 전용 환경 가정)
        time.sleep(0.5)
    return None


def _print_result(label: str, ok: bool, elapsed: float, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}  ({elapsed:.0f} ms)"
          + (f"\n         {detail}" if detail else ""))


# ── classify E2E ─────────────────────────────────────────────

def test_classify(ch, timeout: int) -> dict | None:
    print("\n── classify E2E ──────────────────────────────────────")
    req_id = f"e2e-classify-{uuid.uuid4().hex[:8]}"
    payload = {
        "request_id": req_id,
        "emailId":    "test-email-001",
        "threadId":   "thread-001",
        "subject":    "납품 일정 문의",
        "body":       "이번 달 납품 일정을 알려주시겠어요? 빠른 확인 부탁드립니다.",
        "mail_tone":  "정중체",
    }

    print(f"  Publish  → {CLASSIFY_IN}  request_id={req_id}")
    t0 = time.perf_counter()
    _publish(ch, APP2AI_EXCHANGE, CLASSIFY_IN, payload)

    resp = _poll(ch, CLASSIFY_OUT, req_id, timeout)
    elapsed = (time.perf_counter() - t0) * 1000

    if resp is None:
        _print_result("classify response", False, elapsed,
                      f"timeout({timeout}s) — consumer 실행 중인지 확인")
        return None

    # 필수 필드 검증
    errors = []
    for f in ["request_id", "emailId", "classification", "summary", "email_embedding"]:
        if f not in resp:
            errors.append(f"missing field: {f}")
    if resp.get("request_id") != req_id:
        errors.append(f"request_id mismatch: {resp.get('request_id')}")
    if not isinstance(resp.get("email_embedding"), list):
        errors.append("email_embedding is not a list")
    if resp.get("status") == "error":
        errors.append(f"error response: {resp.get('error_message')}")

    ok = len(errors) == 0
    _print_result("classify response",  ok, elapsed,
                  " | ".join(errors) if errors else "")
    if ok:
        print(f"         domain={resp['classification'].get('domain')} "
              f"intent={resp['classification'].get('intent')}")
        meta = resp.get("meta") or {}
        if meta:
            print(f"         meta.elapsed_ms={meta.get('elapsed_ms')} "
                  f"source={meta.get('source')}")
    return resp


# ── draft E2E ─────────────────────────────────────────────────

def test_draft(ch, timeout: int, classify_resp: dict | None = None):
    print("\n── draft E2E ─────────────────────────────────────────")
    req_id = f"e2e-draft-{uuid.uuid4().hex[:8]}"
    domain = classify_resp["classification"]["domain"] if classify_resp else "업무"
    intent = classify_resp["classification"]["intent"] if classify_resp else "문의"

    payload = {
        "request_id": req_id,
        "mode":       "generate",
        "emailId":    "test-email-001",
        "subject":    "납품 일정 문의",
        "body":       "이번 달 납품 일정을 알려주시겠어요? 빠른 확인 부탁드립니다.",
        "domain":     domain,
        "intent":     intent,
        "summary":    classify_resp["summary"] if classify_resp else "납품 일정 확인 요청",
    }

    print(f"  Publish  → {DRAFT_IN}  request_id={req_id}  mode=generate")
    t0 = time.perf_counter()
    _publish(ch, APP2AI_EXCHANGE, DRAFT_IN, payload)

    resp = _poll(ch, DRAFT_OUT, req_id, timeout)
    elapsed = (time.perf_counter() - t0) * 1000

    if resp is None:
        _print_result("draft generate response", False, elapsed,
                      f"timeout({timeout}s) — consumer 실행 중인지 확인")
        return

    errors = []
    for f in ["request_id", "emailId", "draft_reply", "reply_embedding"]:
        if f not in resp:
            errors.append(f"missing field: {f}")
    if resp.get("request_id") != req_id:
        errors.append(f"request_id mismatch: {resp.get('request_id')}")
    if resp.get("status") == "error":
        errors.append(f"error response: {resp.get('error_message')}")

    ok = len(errors) == 0
    _print_result("draft generate response", ok, elapsed,
                  " | ".join(errors) if errors else "")
    if ok:
        reply_preview = (resp["draft_reply"] or "")[:60].replace("\n", " ")
        print(f"         reply_preview={reply_preview!r}")
        meta = resp.get("meta") or {}
        if meta:
            print(f"         meta.elapsed_ms={meta.get('elapsed_ms')} "
                  f"source={meta.get('source')}")

    # regenerate validation 오류 응답 테스트
    _test_draft_validation_error(ch, domain, intent, timeout)


def _test_draft_validation_error(ch, domain: str, intent: str, timeout: int):
    """mode=regenerate + previous_draft 누락 → ErrorResponse 수신 확인"""
    req_id = f"e2e-regen-{uuid.uuid4().hex[:8]}"
    payload = {
        "request_id": req_id,
        "mode":       "regenerate",
        "emailId":    "test-email-001",
        "subject":    "납품 일정 문의",
        "body":       "이번 달 납품 일정을 알려주시겠어요?",
        "domain":     domain,
        "intent":     intent,
        "summary":    "납품 일정 확인 요청",
        # previous_draft 의도적으로 누락
    }

    print(f"\n  Publish  → {DRAFT_IN}  request_id={req_id}  mode=regenerate (no previous_draft)")
    t0 = time.perf_counter()
    _publish(ch, APP2AI_EXCHANGE, DRAFT_IN, payload)

    resp = _poll(ch, DRAFT_OUT, req_id, timeout)
    elapsed = (time.perf_counter() - t0) * 1000

    if resp is None:
        _print_result("draft regenerate validation error", False, elapsed,
                      f"timeout({timeout}s)")
        return

    ok = (resp.get("status") == "error"
          and resp.get("error_code") == "VALIDATION_ERROR"
          and resp.get("request_id") == req_id)
    detail = f"error_code={resp.get('error_code')}  msg={resp.get('error_message')}"
    _print_result("draft regenerate validation error", ok, elapsed, detail)


# ── 메인 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI 서버 E2E 테스트")
    parser.add_argument("--timeout",       type=int, default=30)
    parser.add_argument("--classify-only", action="store_true")
    parser.add_argument("--draft-only",    action="store_true")
    args = parser.parse_args()

    print(f"RabbitMQ: {RABBITMQ_URL}")
    print(f"Timeout : {args.timeout}s")

    try:
        conn, ch = _connect()
    except pika.exceptions.AMQPConnectionError as e:
        print(f"\n[ERROR] RabbitMQ 연결 실패: {e}")
        sys.exit(1)

    try:
        _declare(ch)

        classify_resp = None
        if not args.draft_only:
            classify_resp = test_classify(ch, args.timeout)

        if not args.classify_only:
            test_draft(ch, args.timeout, classify_resp)

    finally:
        if not conn.is_closed:
            conn.close()

    print("\n──────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
