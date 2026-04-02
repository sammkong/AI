"""
SBERT 임베딩 로드 및 동작 확인 스크립트
실행: python test_sbert.py  (프로젝트 루트에서)
"""

import sys
from pathlib import Path

# src/ 를 import 경로에 추가
sys.path.append(str(Path(__file__).parent / "src"))

from sentence_transformers import SentenceTransformer

SBERT_MODEL_PATH = Path(__file__).parent / "models" / "sbert_business_email"

TEST_TEXTS = [
    "안녕하세요. 이번 프로젝트 마감일이 언제인지 확인 부탁드립니다.",
    "첨부 파일 검토 후 승인 여부를 알려주시기 바랍니다.",
    "회의 일정을 다음 주 화요일로 변경 가능한지 문의드립니다.",
]


def main():
    # 1. 모델 로드
    print(f"[1] 모델 로드 경로: {SBERT_MODEL_PATH}")
    assert SBERT_MODEL_PATH.exists(), f"모델 경로 없음: {SBERT_MODEL_PATH}"

    model = SentenceTransformer(str(SBERT_MODEL_PATH))
    print("    로드 완료\n")

    # 2. 단일 텍스트 encode
    print("[2] 단일 텍스트 encode 테스트")
    single = TEST_TEXTS[0]
    emb_single = model.encode([single], normalize_embeddings=True)
    print(f"    입력: {single}")
    print(f"    shape : {emb_single.shape}")          # (1, 384)
    print(f"    dtype : {emb_single.dtype}\n")

    # 3. 배치 encode + shape 확인
    print("[3] 배치 encode (3개 텍스트)")
    emb_batch = model.encode(TEST_TEXTS, normalize_embeddings=True)
    print(f"    shape : {emb_batch.shape}")           # (3, 384)

    # 4. list[float] 변환 확인
    print("\n[4] list[float] 변환 확인")
    embedding_list = emb_batch[0].tolist()
    print(f"    type     : {type(embedding_list)}")
    print(f"    len      : {len(embedding_list)}")
    print(f"    elem type: {type(embedding_list[0])}")
    print(f"    첫 5개  : {[round(v, 6) for v in embedding_list[:5]]}")

    # 5. 정규화 확인 (L2 norm ≈ 1.0)
    import math
    norm = math.sqrt(sum(v ** 2 for v in embedding_list))
    print(f"\n[5] L2 norm (정규화 확인): {norm:.6f}  (1.0에 가까울수록 정상)")

    print("\n모든 테스트 통과")


if __name__ == "__main__":
    main()
