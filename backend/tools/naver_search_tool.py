import asyncio
import logging
from typing import Dict, List

from langchain_core.tools import tool

from tools.perplexity_client import (
    PerplexityClientError,
    PerplexityResponseFormatError,
    search_events_with_perplexity,
)
from utils.conversation_memory import (
    get_shown_facility_names,
    save_search_results,
    set_status,
)

logger = logging.getLogger(__name__)


def _format_results(results: List[Dict[str, str]], query: str) -> str:
    lines = [f"🔍 '{query}' 웹 검색 결과 (Perplexity):\n"]

    for idx, item in enumerate(results, 1):
        name = item.get("name") or "제목 미상"
        location = item.get("location") or "장소 정보 없음"
        description = item.get("description") or "요약 정보 없음"
        link = item.get("link") or ""
        link_text = f'<a href="{link}" target="_blank">👉 상세 보기</a>' if link else "링크 없음"

        lines.append(
            f"{idx}. **{name}**\n"
            f"   - 📍 장소: {location}\n"
            f"   - 📝 내용: {description}\n"
            f"   - {link_text}\n"
        )

    lines.append("ℹ️ 자세한 일정/변경 사항은 각 행사 공식 홈페이지나 최신 공지를 다시 확인해 주세요.")

    return "\n".join(lines)


@tool
async def naver_web_search(query: str, conversation_id: str) -> str:
    """
    Perplexity를 통해 최신 행사/이벤트 정보를 검색합니다.
    """
    if conversation_id:
        set_status(conversation_id, "웹 정보 확인 중..")

    shown_names = set(get_shown_facility_names(conversation_id)) if conversation_id else set()

    try:
        # Perplexity wrapper(search_events_with_perplexity) 를 백그라운드 스레드에서 호출
        raw_results = await asyncio.to_thread(search_events_with_perplexity, query)
    except (PerplexityClientError, PerplexityResponseFormatError) as exc:
        logger.error("Perplexity 검색 오류: %s", exc)
        return f"웹 검색 오류: {exc}"
    except Exception as exc:
        logger.exception("Perplexity 검색 중 알 수 없는 오류")
        return f"웹 검색 중 알 수 없는 오류가 발생했습니다: {exc}"

    filtered_results = []
    for item in raw_results:
        name = item.get("name") or ""
        if name in shown_names:
            continue

        filtered_results.append(
            {
                "name": name or "제목 미상",
                "link": item.get("link", ""),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
            }
        )

    if not filtered_results:
        return "새로운 웹 검색 결과가 없습니다."

    if conversation_id:
        save_data = [
            {"name": i.get("name", ""), "link": i.get("link", "")}
            for i in filtered_results
            if i.get("name") or i.get("link")
        ]
        if save_data:
            save_search_results(conversation_id, save_data, source="web")
            set_status(conversation_id, "웹 검색 결과 정리 중..")

    return _format_results(filtered_results, query)
