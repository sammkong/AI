# ============================================================
# /draft 엔드포인트 테스트 — generate / regenerate
# ============================================================

import pytest
from unittest.mock import patch

MOCK_DRAFT = "안녕하세요. 문의하신 사항에 대해 답변 드립니다."

BASE_GENERATE_PAYLOAD = {
    "request_id": "req-draft-001",
    "mode": "generate",
    "emailId": "email-001",
    "subject": "납품 일정 문의",
    "body": "이번 달 납품 일정을 알려주시겠어요?",
    "domain": "업무",
    "intent": "문의",
    "summary": "납품 일정 확인 요청 이메일입니다.",
}

REGENERATE_PAYLOAD = {
    **BASE_GENERATE_PAYLOAD,
    "mode": "regenerate",
    "previous_draft": MOCK_DRAFT,
}


class TestDraftGenerate:
    def test_generate_returns_required_fields(self, app_client):
        with patch("api.services.draft_service.generate_draft", return_value=MOCK_DRAFT):
            resp = app_client.post("/draft", json=BASE_GENERATE_PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "req-draft-001"
        assert data["emailId"] == "email-001"
        assert data["draft_reply"] == MOCK_DRAFT
        assert isinstance(data["reply_embedding"], list)
        assert len(data["reply_embedding"]) > 0

    def test_generate_missing_subject_returns_422(self, app_client):
        payload = {k: v for k, v in BASE_GENERATE_PAYLOAD.items() if k != "subject"}
        resp = app_client.post("/draft", json=payload)
        assert resp.status_code == 422

    def test_generate_missing_domain_returns_422(self, app_client):
        payload = {k: v for k, v in BASE_GENERATE_PAYLOAD.items() if k != "domain"}
        resp = app_client.post("/draft", json=payload)
        assert resp.status_code == 422


class TestDraftRegenerate:
    def test_regenerate_with_previous_draft_succeeds(self, app_client):
        with patch("api.services.draft_service.generate_draft", return_value=MOCK_DRAFT):
            resp = app_client.post("/draft", json=REGENERATE_PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert data["draft_reply"] == MOCK_DRAFT

    def test_regenerate_without_previous_draft_returns_422(self, app_client):
        """mode=regenerate 인데 previous_draft 없으면 422"""
        payload = {**BASE_GENERATE_PAYLOAD, "mode": "regenerate"}
        resp = app_client.post("/draft", json=payload)
        assert resp.status_code == 422
        assert "previous_draft" in resp.json()["detail"]

    def test_regenerate_with_empty_previous_draft_returns_422(self, app_client):
        """previous_draft 가 빈 문자열이어도 422"""
        payload = {**BASE_GENERATE_PAYLOAD, "mode": "regenerate", "previous_draft": ""}
        resp = app_client.post("/draft", json=payload)
        assert resp.status_code == 422

    def test_generate_mode_does_not_require_previous_draft(self, app_client):
        """mode=generate 일 때 previous_draft 없어도 정상 처리"""
        with patch("api.services.draft_service.generate_draft", return_value=MOCK_DRAFT):
            resp = app_client.post("/draft", json=BASE_GENERATE_PAYLOAD)

        assert resp.status_code == 200
