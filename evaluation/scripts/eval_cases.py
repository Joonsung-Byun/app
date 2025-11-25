"""
케이스 분류/필터링 유틸
- 데이터셋 로드
- 문항별 케이스 태깅
"""

import json
from pathlib import Path
from typing import Dict, List, Any


DEFAULT_DATASET = Path(__file__).parent.parent / "datasets" / "test_questions_prompt_pruned.json"


def load_dataset(path: Path = None) -> Dict[str, Any]:
    """데이터셋 로드 (기본: pruned 파일)"""
    dataset_path = path or DEFAULT_DATASET
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_case_ids(meta: Dict[str, Any], key: str) -> set:
    """메타데이터 case_ids에서 ID 집합 추출"""
    return set(meta.get("case_ids", {}).get(key, []))


def classify_case(item: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """문항을 케이스명으로 분류"""
    et = item.get("expected_tools") or []
    et_set = set(et)
    qid = item.get("id")

    # 메타에 정의된 케이스 ID 우선
    if qid in get_case_ids(meta, "case3_fallback"):
        return "case3_fallback"
    if qid in get_case_ids(meta, "case2_review_rag_first"):
        return "case2_review"
    if qid in get_case_ids(meta, "case4_no_tools") or qid in get_case_ids(meta, "general_no_tools"):
        return "no_tool"

    if not et:
        return "no_tool"
    if "search_facilities" in et_set and "naver_web_search" in et_set:
        return "case3_fallback"
    if et == ["naver_web_search"]:
        return "web"
    if "get_weather_forecast" in et_set and "search_facilities" in et_set:
        return "weather_places"
    if "get_weather_forecast" in et_set:
        return "weather"
    if "search_facilities" in et_set:
        return "case2"
    if "search_map_for_facilities" in et_set or "search_map_by_address" in et_set or "show_map_for_facilities" in et_set:
        return "map"
    return "other"


def partition_by_case(questions: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """케이스별로 리스트를 분할"""
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        c = classify_case(q, meta)
        buckets.setdefault(c, []).append(q)
    return buckets

