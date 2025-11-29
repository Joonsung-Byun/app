import json
import logging
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from perplexity import Perplexity
from datetime import datetime

from config import settings

load_dotenv()

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "응답 전체를 JSON 배열 하나로만 반환하라. 절대 마크다운, 코드펜스, 추가 설명을 쓰지 말고 순수 JSON만 출력하라. "
    "각 요소는 {\"name\": \"...\", \"link\": \"https://...\", \"description\": \"...\", \"location\": \"...\"} 형식이며 모든 필드는 비어 있지 않은 문자열이어야 한다. "
    "link는 https로 시작하는 실제 행사 단일 상세 페이지여야 하고, 목록 페이지라면 해당 행사를 한 번 더 클릭해 가장 깊은 공식 URL을 사용하라. "
    "location에는 지도 검색으로 바로 찾을 수 있는 구체적인 건물/랜드마크/전시장 이름만 넣고, 도시·구 단위나 층/호/룸번호 같은 세부 공간 정보는 제외한다. "
    "사용자 요청에 지역/도시/구가 명시되어 있다면 반드시 그 행사가 실제로 해당 지역(같은 시·도)에서 열리는지 확인하고, 다른 지역 행사는 제외하라. "
    "오늘 이후 일정만 포함하되, 요청 기간(또는 기본 7일) 안에서 결과가 없으면 같은 달 혹은 최대 1개월 앞 미래까지 범위를 넓혀 과거가 아닌 행사를 찾아라. "
    "불확실한 경우 가장 신뢰도 높은 출처를 우선하되, 어떤 상황에서도 빈 배열이나 다른 텍스트를 출력하지 말고 최소 1개 이상의 유효한 항목을 반환하라."
)

USER_PROMPT_TEMPLATE = (
    "오늘 날짜(연-월-일, 요일까지 포함): {today}\n"
    "사용자 요청: {original_query}\n\n"
    "날짜 해석 규칙 (오늘을 기준으로 명확한 구간을 계산해 적용):\n"
    "- 명시 날짜: YYYY-MM-DD, YYYY년 M월 D일, M월 D일 → 반드시 '오늘의 연도'를 기준으로 계산한다. 이미 지났으면 다음 연도로 이동한다. M월만 있으면 올해 해당 달 전체, 이미 지났으면 내년 같은 달.\n"
    "- 상대 날짜: 오늘/내일/모레, X일 뒤/후, X주 뒤/후, 이번주/다음주/다다음주, 이번주말/다음주말/다다음주말.\n"
    "- 요일: 이번주/다음주/다다음주의 특정 요일(월~일) 또는 \"금요일\" 등은 가장 가까운 미래 날짜(연도 포함)로 계산.\n"
    "- 월/연 단위: 이번달/다음달/다다음달은 올해 기준으로 계산하고, 이미 지났으면 다음 연도로 넘긴다. 연말=올해 12월(지났으면 내년), 연초/신정=1월 1주차 등 연도 정보를 반드시 포함해 판단한다.\n"
    "- 기념일 예시: 크리스마스=12월 25일, 크리스마스이브=12월 24일, 할로윈=10월 31일 (이미 지났으면 내년으로).\n"
    "- 예시에 없더라도 모든 상대/절대 날짜 표현을 '오늘 날짜의 연도'까지 포함해 명확한 구간(start~end)으로 계산해 적용하고, 현재 시점보다 과거(이미 지난 연도/월/일)는 제외.\n"
    "- 사용자가 시점을 언급하면 그 구간(start~end)과 **겹치는** 일정만 반환한다. 이미 시작했어도 종료일이 구간 안에 있거나 구간과 겹치면 포함한다. 종료일이 오늘 이전이면 제외.\n"
    "- 언급이 없으면 기본 구간은 오늘부터 7일 이내이며, 이 기간과 겹치는 진행 중 이벤트는 포함한다.\n"
    "- 요청 기간과 겹치지 않거나 종료된 과거 일정은 제외하되, 조건에 맞는 일정이 없으면 오늘 이후 가장 가까운 미래(최대 1개월)로 범위를 넓혀 반드시 결과를 찾아라.\n\n"
    "출력 조건:\n"
    "- 여러 행사 목록/집계 페이지가 아니라, 해당하는 행사를 한 번 더 클릭하여 들어간 후, 각 행사 단일 상세 페이지 URL을 link에 넣어줘.\n"
    "- 출력은 JSON 배열이며 각 항목은 name, link, description, location 필드를 가진 객체야.\n"
    "- description은 반드시 \"기간 해석: YYYY-MM-DD ~ YYYY-MM-DD | ...\" 형태로 시작해 연도까지 명시하고, 이어서 날짜(또는 날짜 범위)와 장소를 한 문장으로 자연스럽게 요약해. \"기간 내 여러 행사\" 같은 모호한 표현은 쓰지 말고 연도까지 포함한 구체적 날짜를 적어.\n"
    "- location에는 지도 검색으로 바로 찾을 수 있는 구체적인 건물/랜드마크/전시장 이름만 넣고, 도시/구/동 수준의 광범위한 지명은 절대 쓰지 마. (예: '부산' X, '벡스코', '부산시민회관' O) 만약 정확한 건물명을 확인할 수 없다면 '장소 미확인'이라고 명시해. "
    "또한 사용자 요청 지역(시/도/구 등)이 있을 경우, 해당 지역 밖 장소는 절대 포함하지 마.\n"
)


class PerplexityClientError(Exception):
    """Perplexity 클라이언트 설정/호출 오류."""


class PerplexityResponseFormatError(Exception):
    """Perplexity 응답 포맷 오류."""


def _build_user_prompt(original_query: str, today: str) -> str:
    return USER_PROMPT_TEMPLATE.format(original_query=original_query, today=today)


def _extract_json_array(text: str) -> str:
    """
    응답 텍스트에서 JSON 배열 부분만 안전하게 추출.
    Perplexity 응답 JSON 파싱 실패 방지
    """
    
    if not text:
        return ""

    cleaned = text.strip()

    # 코드펜스 제거
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()

    # 이미 배열로 시작하면 그대로 사용
    if cleaned.startswith("["):
        return cleaned

    # 본문 중 배열 부분만 추출
    match = re.search(r"\[.*\]", cleaned, flags=re.S)
    if match:
        return match.group(0).strip()

    return ""


def _normalize_results(raw_results: List[Any]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        link = str(item.get("link", "")).strip()
        if not link:
            continue

        normalized.append(
            {
                "name": str(item.get("name", "")).strip() or "제목 미상",
                "link": link,
                "description": str(item.get("description", "")).strip(),
                "location": str(item.get("location", "")).strip(),
            }
        )

    return normalized


def search_events_with_perplexity(original_query: str, model: str = "sonar-pro") -> List[Dict[str, str]]:
    """
    Perplexity wrapper
    Perplexity API를 호출하여 행사/이벤트 정보를 검색합니다.
    
    상세:
    API 키 로드와 오늘 날짜 계산 → 프롬프트 구성.
    Perplexity chat.completions.create 호출.
    응답 JSON을 파싱/정규화해 [{name, link, description, location}, ...] 리스트로 반환.
    호출/파싱 오류를 PerplexityClientError/PerplexityResponseFormatError로 정리.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY") or settings.PERPLEXITY_API_KEY
    if not api_key:
        raise PerplexityClientError("PERPLEXITY_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인하세요.")

    if not original_query:
        raise PerplexityClientError("검색어가 비어 있습니다.")

    now = datetime.now()
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_text = weekday_names[now.weekday()]
    today_text = now.strftime("%Y-%m-%d") + f" ({weekday_text})"

    client = Perplexity(api_key=api_key)
    user_prompt = _build_user_prompt(original_query, today_text)

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
        )
    except Exception as exc:
        logger.error("Perplexity API 호출 실패: %s", exc)
        raise PerplexityClientError(f"Perplexity API 호출 실패: {exc}") from exc

    content = None
    if completion and getattr(completion, "choices", None) and completion.choices:
        message = getattr(completion.choices[0], "message", None)
        content = getattr(message, "content", None) if message else None
    if not content:
        raise PerplexityResponseFormatError("Perplexity 응답이 비어 있습니다.")

    raw_content = str(content).strip()
    logger.warning("Perplexity raw content (first 500 chars): %s", raw_content[:500])
    
    json_str = _extract_json_array(raw_content)
    logger.warning("Perplexity json_str: %s", (json_str[:500] + "...") if len(json_str) > 500 else json_str)
    
    if not json_str:
        logger.error("Perplexity 응답에서 JSON 배열을 찾지 못했습니다. raw=%s", raw_content[:300])
        raise PerplexityResponseFormatError("Perplexity 응답이 비어 있거나 JSON 배열을 찾지 못했습니다.")

    try:
        parsed = json.loads(json_str)
        logger.warning("Perplexity parsed object: %s", parsed)
    except json.JSONDecodeError as exc:
        logger.error("Perplexity 응답 파싱 실패: %s / raw=%s", exc, raw_content[:300])
        raise PerplexityResponseFormatError(f"Perplexity 응답 JSON 파싱 실패: {exc}") from exc

    if not isinstance(parsed, list):
        raise PerplexityResponseFormatError("Perplexity 응답이 JSON 배열 형식이 아닙니다.")

    normalized = _normalize_results(parsed)
    logger.warning("Perplexity normalized: %s", normalized)
    if not normalized:
        raise PerplexityResponseFormatError("Perplexity 응답에서 유효한 항목을 찾지 못했습니다.")

    return normalized
