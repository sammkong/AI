# ============================================================
# 메시지 계약 테스트 (Message Contract Tests)
#
# RabbitMQ / FastAPI 없이 순수 스키마 레벨 검증
#
# 커버 범위
# ----------
# q.2ai.classify  입력 파싱  (ClassifyRequest)
# q.2app.classify 출력 검증 (ClassifyResponse + ResponseMeta)
# q.2ai.draft     입력 파싱  (DraftRequest — generate / regenerate)
# q.2app.draft    출력 검증 (DraftResponse + ResponseMeta)
# q.2app.draft    에러 응답  (ErrorResponse — VALIDATION_ERROR)
# ============================================================

import json
import pytest
from pydantic import ValidationError

from api.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    Classification,
    DraftRequest,
    DraftResponse,
    ResponseMeta,
    ErrorResponse,
)


# ── 픽스처: 표준 입력 메시지 ─────────────────────────────────

@pytest.fixture
def classify_input():
    return {
        "outbox_id":    1,
        "email_id":     1,
        "sender_email": "sender@example.com",
        "sender_name":  "홍길동",
        "subject":      "납품 일정 문의",
        "body_clean":   "이번 달 납품 일정을 알려주시겠어요?",
        "received_at":  "2026-04-06T10:00:00",
    }


@pytest.fixture
def classify_output():
    return {
        "outbox_id":       1,
        "email_id":        1,
        "classification":  {"domain": "업무", "intent": "문의"},
        "summary":         "납품 일정 확인 요청 이메일입니다.",
        "schedule_info":   None,
        "email_embedding": [0.1, 0.2, 0.3],
    }


@pytest.fixture
def draft_generate_input():
    return {
        "request_id": "req-draft-001",
        "mode":       "generate",
        "emailId":    "email-001",
        "subject":    "납품 일정 문의",
        "body":       "이번 달 납품 일정을 알려주시겠어요?",
        "domain":     "업무",
        "intent":     "문의",
        "summary":    "납품 일정 확인 요청 이메일입니다.",
    }


@pytest.fixture
def draft_regenerate_input(draft_generate_input):
    return {
        **draft_generate_input,
        "request_id":     "req-draft-002",
        "mode":           "regenerate",
        "previous_draft": "안녕하세요. 납품 일정 관련하여 답변 드립니다.",
    }


@pytest.fixture
def draft_output():
    return {
        "request_id":    "req-draft-001",
        "emailId":       "email-001",
        "draft_reply":   "안녕하세요. 납품 일정은 이번 달 말로 예정되어 있습니다.",
        "reply_embedding": [0.4, 0.5, 0.6],
    }


# ── q.2ai.classify 입력 파싱 ─────────────────────────────────

class TestClassifyInput:
    def test_valid_message_parses(self, classify_input):
        req = ClassifyRequest(**classify_input)
        assert req.outbox_id    == 1
        assert req.email_id     == 1
        assert req.subject      == "납품 일정 문의"
        assert req.body_clean   == "이번 달 납품 일정을 알려주시겠어요?"

    def test_missing_outbox_id_raises(self, classify_input):
        classify_input.pop("outbox_id")
        with pytest.raises(ValidationError):
            ClassifyRequest(**classify_input)

    def test_missing_subject_raises(self, classify_input):
        classify_input.pop("subject")
        with pytest.raises(ValidationError):
            ClassifyRequest(**classify_input)

    def test_missing_body_clean_raises(self, classify_input):
        classify_input.pop("body_clean")
        with pytest.raises(ValidationError):
            ClassifyRequest(**classify_input)

    def test_json_roundtrip(self, classify_input):
        """JSON 직렬화 → 역직렬화 무결성"""
        raw  = json.dumps(classify_input)
        data = json.loads(raw)
        req  = ClassifyRequest(**data)
        assert req.email_id == classify_input["email_id"]

    def test_camel_case_aliases_parse(self):
        req = ClassifyRequest(
            outboxId=7,
            emailId=11,
            senderEmail="sender@example.com",
            senderName="홍길동",
            subject="회의 일정 안내",
            bodyClean="정제된 본문...",
            receivedAt="2026-04-06T10:00:00",
        )
        assert req.outbox_id == 7
        assert req.email_id == 11


# ── q.2app.classify 출력 검증 ────────────────────────────────

class TestClassifyOutput:
    def test_valid_response_parses(self, classify_output):
        resp = ClassifyResponse(**classify_output)
        assert resp.outbox_id == 1
        assert resp.classification.domain == "업무"
        assert resp.classification.intent == "문의"
        assert isinstance(resp.email_embedding, list)
        assert all(isinstance(v, float) for v in resp.email_embedding)

    def test_schedule_info_optional(self, classify_output):
        classify_output["schedule_info"] = None
        resp = ClassifyResponse(**classify_output)
        assert resp.schedule_info is None

    def test_schedule_info_with_dict(self, classify_output):
        classify_output["schedule_info"] = {
            "date": "2026-04-10", "time": "14:00",
            "location": "회의실 A", "attendees": ["홍길동"],
        }
        resp = ClassifyResponse(**classify_output)
        assert resp.schedule_info["date"] == "2026-04-10"

    def test_embedding_must_be_float_list(self, classify_output):
        classify_output["email_embedding"] = [0.1, 0.2, 0.3]
        resp = ClassifyResponse(**classify_output)
        assert len(resp.email_embedding) == 3

    def test_outbox_id_preserved(self, classify_output):
        """outbox_id 가 입력과 동일하게 출력에 포함되어야 함"""
        resp = ClassifyResponse(**classify_output)
        assert resp.outbox_id == classify_output["outbox_id"]

    def test_json_serializable(self, classify_output):
        resp = ClassifyResponse(**classify_output)
        dumped = resp.model_dump()
        raw = json.dumps(dumped)            # JSON 직렬화 가능해야 함
        assert "outbox_id" in json.loads(raw)


# ── q.2ai.draft 입력 파싱 (generate) ────────────────────────

class TestDraftGenerateInput:
    def test_valid_generate_parses(self, draft_generate_input):
        req = DraftRequest(**draft_generate_input)
        assert req.mode       == "generate"
        assert req.request_id == "req-draft-001"
        assert req.previous_draft is None

    def test_previous_draft_absent_is_ok_for_generate(self, draft_generate_input):
        req = DraftRequest(**draft_generate_input)
        assert req.previous_draft is None

    def test_missing_domain_raises(self, draft_generate_input):
        draft_generate_input.pop("domain")
        with pytest.raises(ValidationError):
            DraftRequest(**draft_generate_input)

    def test_missing_intent_raises(self, draft_generate_input):
        draft_generate_input.pop("intent")
        with pytest.raises(ValidationError):
            DraftRequest(**draft_generate_input)

    def test_json_roundtrip(self, draft_generate_input):
        raw  = json.dumps(draft_generate_input)
        data = json.loads(raw)
        req  = DraftRequest(**data)
        assert req.mode == "generate"


# ── q.2ai.draft 입력 파싱 (regenerate) ──────────────────────

class TestDraftRegenerateInput:
    def test_valid_regenerate_parses(self, draft_regenerate_input):
        req = DraftRequest(**draft_regenerate_input)
        assert req.mode           == "regenerate"
        assert req.previous_draft is not None
        assert len(req.previous_draft) > 0

    def test_regenerate_without_previous_draft_passes_schema(self, draft_generate_input):
        """
        스키마 레벨에서는 previous_draft 가 Optional 이므로 파싱은 성공.
        비즈니스 검증(ValueError)은 draft_service.run_draft 에서 수행.
        """
        payload = {**draft_generate_input, "mode": "regenerate"}
        req = DraftRequest(**payload)
        assert req.previous_draft is None   # 스키마는 허용

    def test_request_id_preserved(self, draft_regenerate_input):
        req = DraftRequest(**draft_regenerate_input)
        assert req.request_id == "req-draft-002"


# ── q.2app.draft 출력 검증 ───────────────────────────────────

class TestDraftOutput:
    def test_valid_response_parses(self, draft_output):
        resp = DraftResponse(**draft_output)
        assert resp.request_id  == "req-draft-001"
        assert resp.emailId     == "email-001"
        assert len(resp.draft_reply) > 0
        assert isinstance(resp.reply_embedding, list)
        assert all(isinstance(v, float) for v in resp.reply_embedding)

    def test_request_id_preserved(self, draft_output):
        resp = DraftResponse(**draft_output)
        assert resp.request_id == draft_output["request_id"]

    def test_json_serializable(self, draft_output):
        resp = DraftResponse(**draft_output)
        raw  = json.dumps(resp.model_dump())
        assert "draft_reply" in json.loads(raw)

    def test_missing_draft_reply_raises(self, draft_output):
        draft_output.pop("draft_reply")
        with pytest.raises(ValidationError):
            DraftResponse(**draft_output)

    def test_missing_reply_embedding_raises(self, draft_output):
        draft_output.pop("reply_embedding")
        with pytest.raises(ValidationError):
            DraftResponse(**draft_output)


# ── ResponseMeta 검증 ────────────────────────────────────────

class TestResponseMeta:
    def test_valid_meta_parses(self):
        meta = ResponseMeta(elapsed_ms=123.4, source="consumer.classify")
        assert meta.elapsed_ms == 123.4
        assert meta.source     == "consumer.classify"

    def test_source_defaults_to_ai_server(self):
        meta = ResponseMeta(elapsed_ms=50.0)
        assert meta.source == "ai-server"

    def test_meta_embedded_in_classify_response(self, classify_output):
        classify_output["meta"] = {"elapsed_ms": 99.9, "source": "consumer.classify"}
        resp = ClassifyResponse(**classify_output)
        assert resp.meta is not None
        assert resp.meta.elapsed_ms == 99.9
        assert resp.meta.source     == "consumer.classify"

    def test_meta_absent_is_none(self, classify_output):
        resp = ClassifyResponse(**classify_output)
        assert resp.meta is None

    def test_meta_embedded_in_draft_response(self, draft_output):
        draft_output["meta"] = {"elapsed_ms": 210.5, "source": "consumer.draft"}
        resp = DraftResponse(**draft_output)
        assert resp.meta is not None
        assert resp.meta.elapsed_ms == 210.5

    def test_meta_json_serializable(self, classify_output):
        classify_output["meta"] = {"elapsed_ms": 77.0, "source": "consumer.classify"}
        resp = ClassifyResponse(**classify_output)
        dumped = json.dumps(resp.model_dump())
        parsed = json.loads(dumped)
        assert parsed["meta"]["elapsed_ms"] == 77.0


# ── ErrorResponse 검증 ───────────────────────────────────────

class TestErrorResponse:
    @pytest.fixture
    def err_dict(self):
        return {
            "request_id":    "req-draft-err-001",
            "emailId":       "email-001",
            "error_code":    "VALIDATION_ERROR",
            "error_message": "mode=regenerate 일 때 previous_draft 는 필수입니다.",
        }

    def test_valid_error_parses(self, err_dict):
        err = ErrorResponse(**err_dict)
        assert err.request_id    == "req-draft-err-001"
        assert err.status        == "error"
        assert err.error_code    == "VALIDATION_ERROR"
        assert err.error_message != ""

    def test_status_defaults_to_error(self, err_dict):
        err = ErrorResponse(**err_dict)
        assert err.status == "error"

    def test_meta_in_error_response(self, err_dict):
        err_dict["meta"] = {"elapsed_ms": 5.2, "source": "consumer.draft"}
        err = ErrorResponse(**err_dict)
        assert err.meta is not None
        assert err.meta.elapsed_ms == 5.2

    def test_request_id_preserved(self, err_dict):
        err = ErrorResponse(**err_dict)
        assert err.request_id == err_dict["request_id"]

    def test_missing_request_id_raises(self, err_dict):
        err_dict.pop("request_id")
        with pytest.raises(ValidationError):
            ErrorResponse(**err_dict)

    def test_missing_error_code_raises(self, err_dict):
        err_dict.pop("error_code")
        with pytest.raises(ValidationError):
            ErrorResponse(**err_dict)

    def test_json_serializable(self, err_dict):
        err    = ErrorResponse(**err_dict)
        dumped = json.dumps(err.model_dump())
        parsed = json.loads(dumped)
        assert parsed["status"]     == "error"
        assert parsed["error_code"] == "VALIDATION_ERROR"
