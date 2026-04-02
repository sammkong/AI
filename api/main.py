# ============================================================
# FastAPI 앱 진입점
# 서버 시작 시 파이프라인 한 번만 로드 → 전 엔드포인트 공유
# ============================================================

import sys
import os

# src/ 디렉토리를 import 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi import FastAPI
from contextlib import asynccontextmanager

from inference import load_pipeline, predict_email
from api.routers import classify, summarize, draft


# ── 서버 시작/종료 시 실행 ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시: 모델 로드 (한 번만 로드, 메모리 유지)
    print("[Startup] 파이프라인 로딩 중...")
    model = load_pipeline()
    app.state.pipeline = {
        "model"  : model,
        "predict": predict_email,   # 함수도 같이 저장
    }
    print("[Startup] 파이프라인 로드 완료")

    yield  # 서버 실행 중

    # 서버 종료 시: 필요 시 정리 작업
    print("[Shutdown] 서버 종료")


# ── FastAPI 앱 생성 ──────────────────────────────────────────
app = FastAPI(
    title="Business Email AI Server",
    description="이메일 분류 + 요약 + 답장 초안 자동화 API",
    version="1.0.0",
    lifespan=lifespan,
)


# ── 라우터 등록 ──────────────────────────────────────────────
app.include_router(classify.router,  tags=["Classification"])
app.include_router(summarize.router, tags=["Summarization"])
app.include_router(draft.router,     tags=["Draft"])


# ── 헬스체크 ────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── 로컬 실행 ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
