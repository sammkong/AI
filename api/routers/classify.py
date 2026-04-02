# ============================================================
# /classify 엔드포인트 — 비즈니스 로직은 classify_service 에 위임
# ============================================================

from fastapi import APIRouter, HTTPException, Request

from api.schemas import ClassifyRequest, ClassifyResponse
from api.services.classify_service import run_classify

router = APIRouter()


@router.post("/classify", response_model=ClassifyResponse)
async def classify_email(payload: ClassifyRequest, request: Request):
    try:
        return run_classify(payload, request.app.state.pipeline)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
