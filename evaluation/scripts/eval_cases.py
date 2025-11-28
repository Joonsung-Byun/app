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
    category = item.get("category")

    # 메타에 정의된 케이스 ID가 있으면 우선 사용
    if category and qid in get_case_ids(meta, category):
        return category

    if qid in get_case_ids(meta, "cafe_review") or "naver_cafe_search" in et_set:
        return "cafe_review"
    if qid in get_case_ids(meta, "fallback") or ({"search_facilities", "naver_web_search"} <= et_set):
        return "fallback"
    if qid in get_case_ids(meta, "weather_plus") or ({"get_weather_forecast", "search_facilities"} <= et_set):
        return "weather_plus"
    if qid in get_case_ids(meta, "weather") or et == ["get_weather_forecast"]:
        return "weather"
    if qid in get_case_ids(meta, "rag") or et == ["search_facilities"]:
        return "rag"
    if qid in get_case_ids(meta, "web_event") or et == ["naver_web_search"]:
        return "web_event"
    if qid in get_case_ids(meta, "map") or any(t in et_set for t in ["search_map_by_address", "show_map_for_facilities", "search_map_for_facilities"]):
        return "map"
    if not et or qid in get_case_ids(meta, "no_tool"):
        return "no_tool"
    return "other"


def partition_by_case(questions: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """케이스별로 리스트를 분할"""
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        c = classify_case(q, meta)
        buckets.setdefault(c, []).append(q)
    return buckets
