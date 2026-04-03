# RabbitMQ Topology Spec (Infra Defined)
# 인프라 문서 - 시스템 환경 설정(Terraform/Ops) 기준

## ❗ IMPORTANT

- RabbitMQ resources (exchange, queue, binding)는 **코드에서 생성하면 안됨**
- 반드시 **이미 생성된 리소스를 사용만 해야 함**
- (Terraform / Infra 팀에서 관리)

---

## Exchange

### x.app2ai.direct
- type: direct
- durable: true

### x.ai2app.direct
- type: direct
- durable: true

### x.retry.direct
- type: direct
- durable: true

### default exchange
- DLQ 처리용

---

## Queue

### q.2ai.classify
- publisher: App Server
- consumer: AI Server
- routing key: 2ai.classify
- DLX: x.retry.direct
- DL routing key: 2ai.classify.retry

### q.2ai.draft
- publisher: App Server
- consumer: AI Server
- routing key: 2ai.draft
- DLX: x.retry.direct
- DL routing key: 2ai.draft.retry

### q.2app.classify
- publisher: AI Server
- consumer: App Server
- routing key: 2app.classify
- DLX: x.retry.direct
- DL routing key: 2app.classify.retry

### q.2app.draft
- publisher: AI Server
- consumer: App Server
- routing key: 2app.draft
- DLX: x.retry.direct
- DL routing key: 2app.draft.retry

---

## Retry Queue (TTL 기반)

- TTL: 30000ms (30초)
- 3회 재시도 후 실패 시 DLQ 이동

---

## DLQ

### q.dlx.failed
- 최종 실패 메시지 저장
- default exchange 사용

---

## QoS 정책

- prefetch_count = 1 (필수)

이유:
- LLM 호출 비용 높음
- 중복 호출 방지
- retry count 정확성 보장
- AFTER_COMMIT → SSE 순서 보장

---

## Consumer 정책

- queue_declare ❌ 금지
- exchange_declare ❌ 금지
- queue_bind ❌ 금지

- basic_consume + basic_ack만 사용

---

## Publish 정책

- exchange 지정 필수
- routing_key는 반드시 spec에 맞게 사용

---