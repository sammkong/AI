# ============================================================
# Request / Response 스키마 정의 — AI_SYSTEM_SPEC 기준
# ============================================================

from pydantic import BaseModel
from typing import Optional, List


# ── 공통 메타 블록 ───────────────────────────────────────────
class ResponseMeta(BaseModel):
    """
    선택적 메타 블록 — consumer 가 populate, HTTP 라우터는 null.
    백엔드 SLA 모니터링 / 디버깅 용도.
    """
    elapsed_ms: float       # 메시지 수신 ~ publish 까지 처리 시간
    source: str = "ai-server"   # 처리 주체 식별자


# ── 표준화 에러 응답 ─────────────────────────────────────────
class ErrorResponse(BaseModel):
    """
    비즈니스 로직 오류 시 q.2app.* 로 publish 되는 에러 응답.
    request_id / emailId 는 원본 메시지 그대로 보존.

    error_code 목록
    ---------------
    VALIDATION_ERROR   : regenerate 시 previous_draft 누락 등 입력 오류
    PROCESSING_ERROR   : Claude/GPT API 실패 등 일시적 처리 오류
    """
    request_id:    str
    emailId:       str
    status:        str = "error"
    error_code:    str      # VALIDATION_ERROR | PROCESSING_ERROR
    error_message: str
    meta:          Optional[ResponseMeta] = None


# ── /classify ───────────────────────────────────────────────
class ClassifyRequest(BaseModel):
    request_id: str
    emailId:    str
    threadId:   Optional[str] = None
    subject:    str
    body:       str
    mail_tone:  Optional[str] = "정중체"


class Classification(BaseModel):
    domain: str
    intent: str


class ClassifyResponse(BaseModel):
    request_id:      str
    emailId:         str
    classification:  Classification
    summary:         str
    schedule_info:   Optional[dict] = None
    email_embedding: List[float]
    meta:            Optional[ResponseMeta] = None   # consumer 가 populate


# ── /draft ──────────────────────────────────────────────────
class DraftRequest(BaseModel):
    request_id:     str
    mode:           str           # "generate" or "regenerate"
    emailId:        str
    subject:        str
    body:           str
    domain:         str
    intent:         str
    summary:        str
    previous_draft: Optional[str] = None   # regenerate 시 필수


class DraftResponse(BaseModel):
    request_id:      str
    emailId:         str
    draft_reply:     str
    reply_embedding: List[float]
    meta:            Optional[ResponseMeta] = None   # consumer 가 populate


# ── /summarize (보조 엔드포인트) ─────────────────────────────
class SummarizeResponse(BaseModel):
    emailId:  str
    summary:  str
    schedule: Optional[dict] = None
