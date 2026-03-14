# ============================================================
# 임베딩 품질 검증 / F1-score / Confusion Matrix 시각화
# Confusion Matrix → outputs/figures/ 저장
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm

from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics.pairwise import cosine_similarity

from config import FIGURES_DIR, LR_KFOLD

# ── 한글 폰트 설정 ──────────────────────────────────────────
def _set_korean_font() -> None:
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rcParams["font.family"]        = font_name
        plt.rcParams["axes.unicode_minus"] = False
        sns.set_theme(font=font_name)
    else:
        print("[경고] NanumGothic 폰트를 찾을 수 없습니다. notebook Cell 1에서 폰트 설치 여부를 확인하세요.")

_set_korean_font()

def validate_embeddings(X: np.ndarray, df: pd.DataFrame) -> None:
    """SBERT 임베딩 품질 검증 — cosine similarity / mean / std"""
    print("=" * 50)
    print("SBERT 임베딩 품질 검증")
    print("=" * 50)
    print(f"  Shape : {X.shape} | Mean: {np.mean(X):.4f} | Std: {np.std(X):.4f}")

    same_mask = df["intent"] == df["intent"].iloc[0]
    same_idx  = df[same_mask].index[:2].tolist()
    diff_idx  = df[~same_mask].index[0]

    print(f"\n[Cosine Similarity 샘플 검증]")
    print(f"  같은 Intent : {cosine_similarity(X[same_idx[0]].reshape(1,-1), X[same_idx[1]].reshape(1,-1))[0][0]:.4f}  ← 높을수록 좋음")
    print(f"  다른 Intent : {cosine_similarity(X[same_idx[0]].reshape(1,-1), X[diff_idx].reshape(1,-1))[0][0]:.4f}  ← 낮을수록 좋음")
    print(f"  랜덤 (0,100): {cosine_similarity(X[0].reshape(1,-1), X[100].reshape(1,-1))[0][0]:.4f}")

    print(f"\n[도메인별 Intra-class 평균 Cosine Similarity]")
    for domain in df["domain"].unique():
        idxs = df[df["domain"] == domain].index.tolist()[:20]
        if len(idxs) < 2:
            continue
        sims = cosine_similarity(X[idxs])
        np.fill_diagonal(sims, np.nan)
        print(f"  {domain:<25}: {np.nanmean(sims):.4f}")


def evaluate_classifier(
    clf        ,
    X          : np.ndarray,
    y_enc      : np.ndarray,
    label_names: list,
    title      : str,
    fig_filename: str,
    cmap       : str = "Blues",
    n_splits   : int = LR_KFOLD,
) -> None:
    """
    K-Fold F1 (weighted + macro) + cross_val_predict → Confusion Matrix
    fig_filename : 파일명만 전달 (예: "domain_confusion_matrix.png")
                   → 자동으로 outputs/figures/ 에 저장
    """
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    cv_w = cross_val_score(clf, X, y_enc, cv=cv, scoring="f1_weighted")
    cv_m = cross_val_score(clf, X, y_enc, cv=cv, scoring="f1_macro")

    print(f"\n[{title}] K-Fold 결과")
    print(f"  Weighted F1 : {cv_w.mean():.4f} ± {cv_w.std():.4f}")
    print(f"  Macro F1    : {cv_m.mean():.4f} ± {cv_m.std():.4f}")

    y_pred = cross_val_predict(clf, X, y_enc, cv=cv)
    print(f"\n[{title}] Classification Report")
    print(classification_report(y_enc, y_pred, target_names=label_names, zero_division=0))

    # Confusion Matrix → outputs/figures/ 저장
    cm       = confusion_matrix(y_enc, y_pred)
    fig_h    = max(5, len(label_names))
    save_path = os.path.join(FIGURES_DIR, fig_filename)

    plt.figure(figsize=(fig_h + 2, fig_h))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap=cmap,
        xticklabels=label_names,
        yticklabels=label_names,
        linewidths=0.5
    )
    plt.title(f"{title} — Confusion Matrix", fontsize=13)
    plt.xlabel("Predicted", fontsize=11)
    plt.ylabel("True", fontsize=11)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()
    print(f"Confusion Matrix 저장 → {save_path}")