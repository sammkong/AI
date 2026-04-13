# AI 학습 서버 아키텍처 및 Job 처리 설계 (최종 기준)

---

## 1. 목적

본 문서는 AI 학습 서버의 재학습(MLOps) 구조를 정의한다.
특히 관리자 웹에서 발생하는 재학습 요청을 안정적으로 처리하기 위해
**REST + Queue 기반 Job 처리 아키텍처**를 기준으로 설계한다.

본 설계는 다음을 목표로 한다:

* 학습 작업을 비동기 Job 형태로 처리
* Backend와 AI 서버 간 책임 분리
* 기존 classify 메시지 큐 구조 재사용
* 운영 안정성을 고려한 모델 관리 구조 확보

---

## 2. 설계 원칙

### 2.1 역할 분리

* REST API

  * Job 생성
  * 상태 조회
  * 모델 관리

* RabbitMQ

  * 작업 요청 전달
  * 작업 완료 이벤트 전달

---

### 2.2 비동기 처리 원칙

* 모든 학습 작업은 Job 단위로 처리한다
* REST 요청은 즉시 응답해야 한다
* 실제 학습은 Worker에서 수행한다

---

### 2.3 큐 분리 원칙

* 추론과 학습은 반드시 분리한다

| 구분 | 큐              |
| -- | -------------- |
| 추론 | q.2ai.classify |
| 학습 | q.2ai.training |

---

## 3. 전체 시스템 흐름

```text
관리자 웹
→ Backend
→ POST /api/ai-training/training-jobs
→ Job 생성 및 DB 저장 (queued)
→ RabbitMQ (q.2ai.training)
→ AI Training Worker
→ 학습 수행
→ 모델 저장
→ RabbitMQ (q.2app.training)
→ Backend
→ 상태 업데이트
→ 관리자 웹 (GET 조회)
```

---

## 4. REST API 정의

### 4.1 데이터셋 관리

* GET /api/ai-training/datasets
  데이터셋 목록 조회

* POST /api/ai-training/dataset-collections
  데이터 재수집 Job 생성

---

### 4.2 학습 관련 Job 생성

* POST /api/ai-training/preprocessing-jobs
* POST /api/ai-training/pair-jobs
* POST /api/ai-training/training-jobs
* POST /api/ai-training/evaluation-jobs

역할:

* Job 생성
* DB 저장 (status = queued)
* Queue 발행

---

### 4.3 Job 상태 조회

* GET /api/ai-training/jobs/{job_id}

역할:

* Job 상태 확인
* 결과 조회
* UI 표시 데이터 제공

---

### 4.4 모델 관리

* GET /api/ai-training/models
* GET /api/ai-training/models/{model_id}
* PATCH /api/ai-training/models/{model_id}

역할:

* 모델 목록 조회
* 모델 상세 조회
* 운영 모델 전환

---

## 5. Queue 설계

### 5.1 Queue 목록

| 용도     | 큐 이름            |
| ------ | --------------- |
| 학습 요청  | q.2ai.training  |
| 완료 이벤트 | q.2app.training |

---

### 5.2 요청 메시지 스펙

```json
{
  "job_id": "job_001",
  "job_type": "training",
  "task_type": "training",
  "dataset_version": "v3",
  "requested_by": "admin",
  "created_at": "timestamp"
}
```

---

### 5.3 완료 이벤트 메시지 스펙

```json
{
  "job_id": "job_001",
  "status": "completed",
  "model_version": "v2026_04_12_01",
  "finished_at": "timestamp",
  "metrics": {
    "intent_f1": 0.89,
    "domain_accuracy": 0.92
  },
  "error_message": null
}
```

---

## 6. Worker 설계

Training Worker는 다음을 수행한다:

1. q.2ai.training 메시지 수신
2. job_type 기반 작업 분기
3. 학습 코드 실행

   * train_sbert.py
   * train_domain.py
   * train_intent.py
4. 모델 저장
5. 결과 생성
6. q.2app.training으로 완료 이벤트 발행

---

## 7. Backend 역할

* Job 생성 시 DB 저장 (queued)
* Queue 메시지 발행
* 완료 이벤트 수신
* Job 상태 업데이트
* REST API로 상태 제공

---

## 8. 상태 관리

```text
queued → running → completed / failed
```

---

## 9. 모델 관리 전략

### 9.1 버전 관리

* 모델은 덮어쓰기 금지
* 버전 단위로 저장

---

### 9.2 운영 모델 전환

* 학습 완료 후 자동 적용 금지
* PATCH API를 통해 활성 모델 전환

---

### 9.3 롤백

* 이전 모델 유지
* 문제 발생 시 즉시 복구 가능

---

## 10. 임베딩 처리 정책

* SBERT는 AI 서버 내부에서 직접 사용
* 별도 REST API 제공하지 않음
* classify 및 training에서 공통 사용

---

## 11. classify 구조 재사용

본 설계는 기존 classify RabbitMQ 구조를 재사용한다.

* 요청 큐 → 처리 → 결과 큐 패턴 유지
* 동일한 consumer 구조 사용
* Backend ↔ AI 통신 방식 동일

단, 학습 Job은 다음을 추가한다:

* 상태 관리
* 완료 이벤트
* 모델 버전 정보

---

## 12. 설계 요약

* REST는 Job을 생성하고 상태를 조회한다
* RabbitMQ는 작업 요청과 완료 이벤트를 전달한다
* 학습 Job은 classify MQ 구조를 재사용하여 확장한다
* 학습은 Worker에서 비동기로 수행된다
* 모델은 버전 기반으로 관리된다

---

## 13. 향후 확장

* training worker 분리 (독립 서비스)
* 모델 자동 평가 및 승인 프로세스
* 스케줄 기반 재학습
* 실험/운영 모델 분리
* 모니터링 및 알림 시스템 추가