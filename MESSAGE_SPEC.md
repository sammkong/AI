# AI 서버 메시지 명세서

> 최종 수정: 2026-04-02  
> 대상: 백엔드 팀 연동 가이드

---

## 1. RabbitMQ 토폴로지

| 구분 | Exchange | Type | Durable |
|---|---|---|---|
| App → AI | `x.app2ai.direct` | direct | true |
| AI → App | `x.ai2app.direct` | direct | true |

| Queue | Exchange | Routing Key | 방향 |
|---|---|---|---|
| `q.2ai.classify` | x.app2ai.direct | q.2ai.classify | App → AI |
| `q.2ai.draft` | x.app2ai.direct | q.2ai.draft | App → AI |
| `q.2app.classify` | x.ai2app.direct | q.2app.classify | AI → App |
| `q.2app.draft` | x.ai2app.direct | q.2app.draft | AI → App |

- 모든 Exchange / Queue: `durable=true`, `delivery_mode=2` (persistent)
- `content_type`: `application/json`, 인코딩: UTF-8

---

## 2. classify

### 2-1. 요청 — `q.2ai.classify`

```json
{
  "request_id": "uuid-string",
  "emailId":    "string",
  "threadId":   "string | null",
  "subject":    "string",
  "body":       "string",
  "mail_tone":  "정중체"
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| request_id | string | ✅ | 요청 식별자. 응답에 그대로 보존 |
| emailId | string | ✅ | 이메일 식별자 |
| threadId | string | ❌ | 스레드 식별자 (없으면 null) |
| subject | string | ✅ | 이메일 제목 |
| body | string | ✅ | 이메일 본문 |
| mail_tone | string | ❌ | 기본값: "정중체" |

### 2-2. 성공 응답 — `q.2app.classify`

```json
{
  "request_id": "uuid-string",
  "emailId":    "string",
  "classification": {
    "domain": "string",
    "intent": "string"
  },
  "summary":         "string",
  "schedule_info":   { ... } | null,
  "email_embedding": [0.123, 0.456, ...],
  "meta": {
    "elapsed_ms": 234.5,
    "source":     "consumer.classify"
  }
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| request_id | string | 요청의 request_id 그대로 |
| emailId | string | 요청의 emailId 그대로 |
| classification.domain | string | 분류된 도메인 |
| classification.intent | string | 분류된 인텐트 |
| summary | string | GPT 요약 |
| schedule_info | object \| null | 일정 정보. 없으면 null |
| email_embedding | float[] | SBERT 임베딩 벡터 |
| meta.elapsed_ms | float | AI 서버 처리 시간 (ms) |
| meta.source | string | 처리 주체 식별자 |

#### email_embedding 생성 규칙

```
embed_input = summary  (len(summary) >= 10)
            | subject + "\n" + body  (summary 없거나 너무 짧음)
email_embedding = SBERT(embed_input, normalize=True)
```

---

## 3. draft

### 3-1. 요청 — `q.2ai.draft`

```json
{
  "request_id":    "uuid-string",
  "mode":          "generate | regenerate",
  "emailId":       "string",
  "subject":       "string",
  "body":          "string",
  "domain":        "string",
  "intent":        "string",
  "summary":       "string",
  "previous_draft": "string | null"
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| request_id | string | ✅ | 요청 식별자 |
| mode | string | ✅ | `generate` 또는 `regenerate` |
| emailId | string | ✅ | 이메일 식별자 |
| subject | string | ✅ | 이메일 제목 |
| body | string | ✅ | 이메일 본문 |
| domain | string | ✅ | classify 결과 domain |
| intent | string | ✅ | classify 결과 intent |
| summary | string | ✅ | classify 결과 summary |
| previous_draft | string | **regenerate 시 필수** | 이전 초안. 없으면 `VALIDATION_ERROR` 응답 |

### 3-2. 성공 응답 — `q.2app.draft`

```json
{
  "request_id":      "uuid-string",
  "emailId":         "string",
  "draft_reply":     "string",
  "reply_embedding": [0.123, 0.456, ...],
  "meta": {
    "elapsed_ms": 1420.3,
    "source":     "consumer.draft"
  }
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| request_id | string | 요청의 request_id 그대로 |
| emailId | string | 요청의 emailId 그대로 |
| draft_reply | string | Claude 생성 답장 초안 |
| reply_embedding | float[] | SBERT(draft_reply) 임베딩 벡터 |
| meta.elapsed_ms | float | AI 서버 처리 시간 (ms) |
| meta.source | string | 처리 주체 식별자 |

---

## 4. 에러 응답 (공통)

비즈니스 로직 오류는 에러 응답을 해당 응답 큐로 publish 합니다.  
스키마 손상 / JSON 파싱 실패는 nack 처리하며 에러 응답을 보내지 않습니다.

### 에러 응답 구조

```json
{
  "request_id":    "uuid-string",
  "emailId":       "string",
  "status":        "error",
  "error_code":    "VALIDATION_ERROR",
  "error_message": "mode=regenerate 일 때 previous_draft 는 필수입니다.",
  "meta": {
    "elapsed_ms": 3.2,
    "source":     "consumer.draft"
  }
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| request_id | string | 원본 request_id 보존 |
| emailId | string | 원본 emailId 보존 |
| status | string | 항상 `"error"` |
| error_code | string | 아래 코드 참고 |
| error_message | string | 사람이 읽을 수 있는 오류 설명 |
| meta | object \| null | 처리 시간 포함 (선택) |

### error_code 목록

| error_code | 발생 조건 | 권장 처리 |
|---|---|---|
| `VALIDATION_ERROR` | `mode=regenerate` 인데 `previous_draft` 없음 | 요청 수정 후 재전송 |
| `PROCESSING_ERROR` | Claude/GPT API 오류 등 일시적 실패 | 잠시 후 재전송 |

---

## 5. ack / nack 정책

| 상황 | 처리 | 이유 |
|---|---|---|
| 정상 처리 완료 | `ack` | — |
| JSON 파싱 실패 | `nack(requeue=False)` | 손상 메시지는 재시도 불가 → DLQ |
| Pydantic 검증 실패 | `nack(requeue=False)` | 스키마 불일치는 재시도 불가 → DLQ |
| 비즈니스 로직 오류 (`ValueError`) | `ErrorResponse publish` + `ack` | 앱이 피드백 수신, 재시도 방지 |
| 일시적 오류 (API 다운 등) | `nack(requeue=True)` | 재시도 가능 |

> **무한 재시도 방지**: `requeue=True` 를 사용하는 경우 DLQ + `x-death` 헤더 카운팅 또는 메시지 TTL 설정을 권장합니다.

---

## 6. meta 블록

모든 성공 응답 및 에러 응답에 `meta` 블록이 포함됩니다.

- **목적**: AI 서버 처리 시간 모니터링, SLA 측정, 디버깅
- **기준**: 메시지 수신 ~ publish 완료까지 측정
- **HTTP API** (`/classify`, `/draft`): `meta` 필드는 `null` (consumer 경로에서만 populate)
- **backward compatible**: 기존 클라이언트가 `meta` 필드를 무시해도 동작 이상 없음

```json
"meta": {
  "elapsed_ms": 234.5,
  "source":     "consumer.classify"
}
```

---

## 7. 공통 규칙

1. `request_id` 는 AI 서버가 절대 변경하지 않으며 응답에 그대로 반영
2. AI 서버는 데이터를 저장하지 않음 (stateless)
3. 임베딩은 반드시 `list[float]` 형태
4. 모든 응답은 JSON only
5. SBERT 모델은 fine-tuned 모델 고정 (신규 임베딩 모델 미사용)
6. Claude 모델: `draft` / GPT 모델: `classify`

---

## 8. 메시지 흐름 요약

```
App
 │
 ├─ q.2ai.classify ──▶ [consumer_classify] ──▶ q.2app.classify ──▶ App
 │                            │
 │                       (GPT 요약 + SBERT 임베딩 + 분류)
 │
 └─ q.2ai.draft ────▶ [consumer_draft]    ──▶ q.2app.draft    ──▶ App
                             │
                        (Claude 초안 + SBERT 임베딩)
```
