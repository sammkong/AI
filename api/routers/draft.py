# ============================================================
# /draft 엔드포인트 — 비즈니스 로직은 draft_service 에 위임
# ============================================================

from fastapi import APIRouter, HTTPException, Request

from api.schemas import DraftRequest, DraftResponse
from api.services.draft_service import run_draft

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
async def draft_email(payload: DraftRequest, request: Request):
    try:
        return run_draft(payload, request.app.state.pipeline)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
