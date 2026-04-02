# ============================================================
# draft 비즈니스 로직 — 라우터 / consumer 공용
# ============================================================

from api.schemas import DraftRequest, DraftResponse
from api.services.claude_service import generate_draft


def run_draft(payload: DraftRequest, pipeline: dict) -> DraftResponse:
    """
    Parameters
    ----------
    payload  : DraftRequest (pydantic)
    pipeline : {"model": {...sbert/clf...}, "predict": predict_email}

    Returns
    -------
    DraftResponse (pydantic)

    Raises
    ------
    ValueError
        mode=regenerate 인데 previous_draft 가 없는 경우
        → consumer: publish error + ack  /  router: HTTP 422
    """
    if payload.mode == "regenerate" and not payload.previous_draft:
        raise ValueError("mode=regenerate 일 때 previous_draft 는 필수입니다.")

    draft_reply = generate_draft(
        subject=payload.subject,
        body=payload.body,
        domain=payload.domain,
        intent=payload.intent,
        summary=payload.summary,
        mode=payload.mode,
        previous_draft=payload.previous_draft or "",
    )

    reply_embedding = pipeline["model"]["sbert"].encode(
        [draft_reply], normalize_embeddings=True
    )[0].tolist()

    return DraftResponse(
        request_id=payload.request_id,
        emailId=payload.emailId,
        draft_reply=draft_reply,
        reply_embedding=reply_embedding,
    )
