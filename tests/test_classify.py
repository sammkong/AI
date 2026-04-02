# ============================================================
# /classify 엔드포인트 테스트
# ============================================================

import pytest
from unittest.mock import patch


BASE_PAYLOAD = {
    "request_id": "req-001",
    "emailId": "email-001",
    "threadId": "thread-001",
    "subject": "세금계산서 발행 요청",
    "body": "지난달 납품 건에 대한 세금계산서 발행 부탁드립니다.",
    "mail_tone": "정중체",
}


def _mock_summarize(email_text: str) -> dict:
    return {"summary": "세금계산서 발행 요청 건입니다.", "schedule": None}


def _mock_summarize_short(email_text: str) -> dict:
    return {"summary": "짧음", "schedule": None}  # len < 10 → fallback


def _mock_summarize_empty(email_text: str) -> dict:
    return {"summary": "", "schedule": None}  # 빈 summary → fallback


class TestClassifySuccess:
    def test_returns_required_fields(self, app_client):
        with patch("api.services.classify_service.summarize_email", side_effect=_mock_summarize):
            resp = app_client.post("/classify", json=BASE_PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "req-001"
        assert data["emailId"] == "email-001"
        assert "classification" in data
        assert "domain" in data["classification"]
        assert "intent" in data["classification"]
        assert isinstance(data["email_embedding"], list)
        assert len(data["email_embedding"]) > 0

    def test_embedding_uses_summary_when_valid(self, app_client):
        with patch("api.services.classify_service.summarize_email", side_effect=_mock_summarize) as mock_sum:
            resp = app_client.post("/classify", json=BASE_PAYLOAD)

        assert resp.status_code == 200

    def test_embedding_fallback_on_empty_summary(self, app_client):
        """summary가 빈 문자열이면 email_text 로 fallback"""
        with patch("api.services.classify_service.summarize_email", side_effect=_mock_summarize_empty):
            resp = app_client.post("/classify", json=BASE_PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["email_embedding"], list)

    def test_embedding_fallback_on_short_summary(self, app_client):
        """summary 길이가 MIN_SUMMARY_LENGTH(10) 미만이면 email_text 로 fallback"""
        with patch("api.services.classify_service.summarize_email", side_effect=_mock_summarize_short):
            resp = app_client.post("/classify", json=BASE_PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["email_embedding"], list)


class TestClassifyValidation:
    def test_missing_subject_returns_422(self, app_client):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "subject"}
        resp = app_client.post("/classify", json=payload)
        assert resp.status_code == 422

    def test_missing_body_returns_422(self, app_client):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "body"}
        resp = app_client.post("/classify", json=payload)
        assert resp.status_code == 422
