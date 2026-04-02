# ============================================================
# GPT 연동 서비스 - 이메일 요약 + 일정 추출
# /summarize 엔드포인트에서 호출
# MOCK_MODE=True → 실제 API 호출 없이 테스트 가능
# ============================================================

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Mock 모드 설정 ───────────────────────────────────────────
# 테스트 시 True, 실제 호출 시 False
MOCK_MODE = True


# ── OpenAI 클라이언트 초기화 ─────────────────────────────────
def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


# ── Mock 응답 ────────────────────────────────────────────────
def _mock_response(email_text: str) -> dict:
    """실제 API 호출 없이 테스트용 가짜 응답 반환"""
    return {
        "summary": f"[MOCK] 이메일 요약: {email_text[:30]}...",
        "schedule": {
            "date": "2026-03-25",
            "time": "14:00",
            "location": "회의실 A",
            "attendees": ["홍길동", "김철수"]
        }
    }


# ── 프롬프트 생성 ────────────────────────────────────────────
def _build_prompt(email_text: str) -> str:
    return f"""
다음 비즈니스 이메일을 분석하여 아래 JSON 형식으로만 응답하세요.
다른 설명이나 마크다운 없이 JSON만 출력하세요.

[이메일 내용]
{email_text}

[출력 형식]
{{
  "summary": "이메일 핵심 내용을 1~2문장으로 요약",
  "schedule": {{
    "date": "YYYY-MM-DD 형식 (없으면 null)",
    "time": "HH:MM 형식 (없으면 null)",
    "location": "장소 (없으면 null)",
    "attendees": ["참석자 목록 (없으면 빈 배열)"]
  }}
}}

일정 정보가 전혀 없으면 schedule 전체를 null로 설정하세요.
"""


# ── 메인 함수 ────────────────────────────────────────────────
def summarize_email(email_text: str) -> dict:
    """
    이메일 요약 + 일정 추출

    Parameters:
        email_text : subject + body 합친 전처리된 텍스트

    Returns:
        {
            "summary" : str,
            "schedule": dict | None
        }
    """
    # Mock 모드
    if MOCK_MODE:
        print("[GPT Service] MOCK 모드 - 실제 API 호출 없음")
        return _mock_response(email_text)

    # 실제 GPT 호출
    try:
        client = _get_client()
        print("[GPT Service] GPT API 호출 중...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",   # 가장 저렴한 모델
            messages=[
                {
                    "role": "system",
                    "content": "당신은 비즈니스 이메일 분석 전문가입니다. 요청된 JSON 형식으로만 응답합니다."
                },
                {
                    "role": "user",
                    "content": _build_prompt(email_text)
                }
            ],
            temperature=0.1,   # 낮을수록 일관된 출력
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()
        print(f"[GPT Service] 응답 수신 완료")

        # JSON 파싱
        result = json.loads(raw)
        return {
            "summary" : result.get("summary", ""),
            "schedule": result.get("schedule", None),
        }

    except json.JSONDecodeError as e:
        print(f"[GPT Service] JSON 파싱 오류: {e}")
        return {"summary": raw, "schedule": None}

    except Exception as e:
        print(f"[GPT Service] API 호출 오류: {e}")
        raise


# ── 로컬 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        # 일정 있는 케이스
        {
            "label": "일정 있는 이메일",
            "text": "안녕하세요. 다음 주 화요일 오후 2시에 회의실 A에서 분기 실적 검토 회의를 진행하려 합니다. 홍길동, 김철수 참석 부탁드립니다."
        },
        # 일정 없는 케이스
        {
            "label": "일정 없는 이메일",
            "text": "지난달 납품 건에 대한 세금계산서 발행 부탁드립니다. 담당자 확인 후 빠른 처리 부탁드립니다."
        },
    ]

    for tc in test_cases:
        print(f"\n{'='*50}")
        print(f"[테스트] {tc['label']}")
        print(f"입력: {tc['text']}")
        result = summarize_email(tc["text"])
        print(f"결과:")
        print(f"  summary  : {result['summary']}")
        print(f"  schedule : {result['schedule']}")

    print(f"\n{'='*50}")
    print("테스트 완료!")
    print("실제 API 호출하려면 MOCK_MODE = False 로 변경하세요.")
