# ============================================================
# 추론 파이프라인
# FastAPI 등 백엔드 연동 시 이 파일만 import
# ============================================================

import numpy as np
import joblib
from sentence_transformers import SentenceTransformer

from config import (
    SBERT_MODEL_PATH,
    DOMAIN_CLF_PATH, DOMAIN_LE_PATH,
    INTENT_CLF_PATH, INTENT_LE_PATH,
    CONFIDENCE_THRESHOLD,
)


def load_pipeline(
    sbert_path     : str = SBERT_MODEL_PATH,
    domain_clf_path: str = DOMAIN_CLF_PATH,
    domain_le_path : str = DOMAIN_LE_PATH,
    intent_clf_path: str = INTENT_CLF_PATH,
    intent_le_path : str = INTENT_LE_PATH,
) -> dict:
    """저장된 모델 전체 로드 → pipeline dict"""
    pipeline = {
        "sbert"     : SentenceTransformer(sbert_path),
        "domain_clf": joblib.load(domain_clf_path),
        "le_domain" : joblib.load(domain_le_path),
        "intent_clf": joblib.load(intent_clf_path),
        "le_intent" : joblib.load(intent_le_path),
    }
    print("[load_pipeline] ✅ 파이프라인 로드 완료")
    return pipeline


def predict_email(
    email_text          : str,
    pipeline            : dict,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> dict:
    """
    email_text → domain + intent 예측
    SBERT embedding → Domain LR → Intent LR (조건부)
    """
    emb = pipeline["sbert"].encode([email_text], normalize_embeddings=True)

    # 1차: Domain
    domain_proba = pipeline["domain_clf"].predict_proba(emb)[0]
    domain_idx   = np.argmax(domain_proba)
    domain_conf  = domain_proba[domain_idx]
    domain_name  = pipeline["le_domain"].inverse_transform([domain_idx])[0]

    # 2차: Intent (domain 조건부)
    intent_name, intent_conf = "unknown", 0.0
    if domain_name in pipeline["intent_clf"]:
        intent_proba = pipeline["intent_clf"][domain_name].predict_proba(emb)[0]
        intent_idx   = np.argmax(intent_proba)
        intent_conf  = intent_proba[intent_idx]
        intent_name  = pipeline["le_intent"][domain_name].inverse_transform([intent_idx])[0]

    return {
        "domain"            : domain_name,
        "domain_confidence" : round(float(domain_conf), 4),
        "intent"            : intent_name,
        "intent_confidence" : round(float(intent_conf), 4),
        "low_confidence"    : (domain_conf < confidence_threshold) or
                              (intent_conf < confidence_threshold),
    }


def predict_batch(
    email_texts         : list,
    pipeline            : dict,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> list:
    """List[str] → List[dict]"""
    return [predict_email(t, pipeline, confidence_threshold) for t in email_texts]