"""
Tool 사용 정확도 평가 스크립트
- Tool 선택 정확도
- 파라미터 정확도
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Set
import time

# 백엔드 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import numpy as np
from collections import defaultdict
from evaluation.scripts.eval_cases import classify_case, load_dataset


class ToolCallLogger:
    """Tool 호출을 로깅하는 콜백 핸들러"""

    def __init__(self):
        self.tool_calls = []

    def reset(self):
        self.tool_calls = []

    def log_tool_call(self, tool_name: str, tool_input: Dict[str, Any]):
        self.tool_calls.append({
            "tool": tool_name,
            "input": tool_input
        })

    def get_called_tools(self) -> List[str]:
        return [call["tool"] for call in self.tool_calls]


def calculate_tool_selection_accuracy(
    expected_tools: List[str],
    actual_tools: List[str]
) -> float:
    """Tool 선택 정확도 계산"""
    if not expected_tools:
        # Tool을 사용하지 않아야 하는 경우
        return 1.0 if not actual_tools else 0.0

    expected_set = set(expected_tools)
    actual_set = set(actual_tools)

    # Jaccard 유사도
    intersection = expected_set & actual_set
    union = expected_set | actual_set

    if not union:
        return 1.0

    return len(intersection) / len(union)


def calculate_parameter_accuracy(
    expected_params: Dict[str, Any],
    actual_calls: List[Dict[str, Any]],
    expected_tools: List[str]
) -> float:
    """파라미터 정확도 계산"""
    if not expected_params:
        return 1.0

    # 예상 Tool의 호출만 필터링
    relevant_calls = [
        call for call in actual_calls
        if call["tool"] in expected_tools
    ]

    if not relevant_calls:
        return 0.0

    # 파라미터 매칭 점수 계산
    total_params = len(expected_params)
    matched_params = 0

    for key, expected_value in expected_params.items():
        for call in relevant_calls:
            actual_value = call.get("input", {}).get(key)
            if actual_value and str(expected_value).lower() in str(actual_value).lower():
                matched_params += 1
                break

    return matched_params / total_params if total_params > 0 else 1.0


def evaluate_tool_accuracy(
    agent,
    test_data: List[Dict[str, Any]],
    tool_logger: ToolCallLogger,
    meta: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Tool 사용 정확도 전체 평가"""
    meta = meta or {}

    def record_from_intermediate_steps(response):
        """AgentExecutor가 반환하는 intermediate_steps에서 tool 호출을 로깅"""
        if not isinstance(response, dict):
            return [], []
        steps = response.get("intermediate_steps") or []
        actual_calls_local = []
        actual_tools_local = []
        for step in steps:
            # step은 (AgentAction, observation) 형태
            if not step or len(step) < 1:
                continue
            action = step[0]
            tool_name = getattr(action, "tool", None)
            tool_input = getattr(action, "tool_input", None)
            if not tool_name:
                continue
            tool_logger.log_tool_call(tool_name, tool_input if isinstance(tool_input, dict) else {"raw": tool_input})
            actual_calls_local.append({"tool": tool_name, "input": tool_input if isinstance(tool_input, dict) else {"raw": tool_input}})
            actual_tools_local.append(tool_name)
        return actual_tools_local, actual_calls_local

    selection_scores = []
    parameter_scores = []
    results = []
    service_success = defaultdict(list)
    per_tool_hits = defaultdict(lambda: {"expected": 0, "hit": 0})

    for i, item in enumerate(test_data):
        question = item["question"]
        expected_tools = item.get("expected_tools", [])
        expected_params = item.get("expected_tool_params", {})
        ctype = classify_case(item, meta)

        print(f"[{i+1}/{len(test_data)}] 평가 중: {question[:30]}...")

        # 로거 리셋
        tool_logger.reset()

        # 에이전트 실행
        try:
            response = agent.invoke({
                "input": question,
                "conversation_id": "eval_session",
                "chat_history": []
            })
            # intermediate_steps에서 tool 호출 추출
            actual_tools, actual_calls = record_from_intermediate_steps(response)
            # fallback: 직접 logger가 가진 값 사용
            if not actual_tools:
                actual_tools = tool_logger.get_called_tools()
            if not actual_calls:
                actual_calls = tool_logger.tool_calls
        except Exception as e:
            print(f"Error for question '{question}': {e}")
            actual_tools = []
            actual_calls = []

        # 점수 계산
        selection_score = calculate_tool_selection_accuracy(expected_tools, actual_tools)
        parameter_score = calculate_parameter_accuracy(expected_params, actual_calls, expected_tools)

        selection_scores.append(selection_score)
        parameter_scores.append(parameter_score)

        # 서비스 품질용 간단 성공 판정 (툴 호출만 기준)
        actual_set = set(actual_tools)
        if ctype == "no_tool":
            success = len(actual_tools) == 0
            desc = "도구를 사용하지 않아야 함"
        elif ctype == "case3_fallback":
            success = ("search_facilities" in actual_set and "naver_web_search" in actual_set)
            desc = "RAG 0건 → web_search까지 호출"
        elif ctype in ("case2", "case2_review"):
            success = "search_facilities" in actual_set
            desc = "시설 검색 호출"
        elif ctype == "web":
            success = "naver_web_search" in actual_set
            desc = "웹 검색 호출"
        elif ctype == "weather_places":
            success = ("get_weather_forecast" in actual_set and "search_facilities" in actual_set)
            desc = "날씨 확인 후 시설 검색 호출"
        elif ctype == "weather":
            success = "get_weather_forecast" in actual_set
            desc = "날씨 조회 호출"
        elif ctype == "map":
            success = any(t in actual_set for t in ["search_map_for_facilities", "search_map_by_address", "show_map_for_facilities"])
            desc = "지도 관련 도구 호출"
        else:
            success = len(actual_tools) == 0
            desc = "기대 도구 없음"

        service_success[ctype].append({"success": success, "description": desc})

        results.append({
            "question": question,
            "expected_tools": expected_tools,
            "actual_tools": actual_tools,
            "expected_params": expected_params,
            "actual_calls": actual_calls,
            "selection_accuracy": selection_score,
            "parameter_accuracy": parameter_score
        })

        # per-tool 통계 (기대된 툴 기준)
        for t in expected_tools:
            per_tool_hits[t]["expected"] += 1
            if t in actual_set:
                per_tool_hits[t]["hit"] += 1

        # Rate limiting
        time.sleep(0.3)

    # 서비스 품질 요약
    by_case = {}
    for ctype, items in service_success.items():
        if not items:
            continue
        succ = [1 if it["success"] else 0 for it in items]
        by_case[ctype] = {
            "success_rate": float(np.mean(succ)),
            "count": len(items),
            "description": items[0]["description"]
        }

    return {
        "summary": {
            "total_evaluated": len(selection_scores),
            "tool_selection_accuracy": {
                "mean": float(np.mean(selection_scores)),
                "std": float(np.std(selection_scores)),
                "min": float(np.min(selection_scores)),
                "max": float(np.max(selection_scores))
            },
            "parameter_accuracy": {
                "mean": float(np.mean(parameter_scores)),
                "std": float(np.std(parameter_scores)),
                "min": float(np.min(parameter_scores)),
                "max": float(np.max(parameter_scores))
            },
            "combined_accuracy": {
                "mean": float(np.mean([s * p for s, p in zip(selection_scores, parameter_scores)])),
            }
        },
        "details": results,
        "by_category": calculate_category_stats(results, test_data),
        "by_tool": {
            tool: {
                "expected": stats["expected"],
                "hit": stats["hit"],
                "success_rate": (stats["hit"] / stats["expected"]) if stats["expected"] else 0.0
            }
            for tool, stats in per_tool_hits.items()
        },
        "service_quality": {
            "by_case": by_case
        }
    }


def calculate_category_stats(
    results: List[Dict[str, Any]],
    test_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """카테고리별 통계 계산"""
    categories = {}

    for result, item in zip(results, test_data):
        category = item.get("category", "unknown")
        if category not in categories:
            categories[category] = {
                "selection_scores": [],
                "parameter_scores": []
            }

        categories[category]["selection_scores"].append(result["selection_accuracy"])
        categories[category]["parameter_scores"].append(result["parameter_accuracy"])

    stats = {}
    for category, scores in categories.items():
        stats[category] = {
            "count": len(scores["selection_scores"]),
            "selection_accuracy": float(np.mean(scores["selection_scores"])),
            "parameter_accuracy": float(np.mean(scores["parameter_scores"]))
        }

    return stats


def main():
    """Tool 정확도 평가 실행"""
    # 테스트 데이터 로드
    data = load_dataset()
    test_questions = data["questions"]

    # Agent 및 Tool Logger 초기화
    try:
        from agent.agent import create_agent

        # Tool 호출 로깅을 위한 래퍼 설정 필요
        # 실제 구현 시 agent의 tool 호출을 가로채는 방식으로 구현
        tool_logger = ToolCallLogger()

        # 주의: 실제 사용 시 agent에 콜백을 연결해야 함
        agent = create_agent()

        print("⚠️ Tool 로깅을 위해 agent에 콜백 핸들러를 연결해야 합니다.")
        print("현재는 기본 평가만 수행됩니다.\n")

        results = evaluate_tool_accuracy(agent, test_questions, tool_logger, meta=data.get("metadata", {}))

        # 결과 저장
        output_path = Path(__file__).parent.parent / "results" / "tool_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"✅ Tool 정확도 평가 완료: {output_path}")
        return results

    except ImportError as e:
        print(f"⚠️ Agent 임포트 실패: {e}")
        print("백엔드의 agents 모듈 경로를 확인해주세요.")
        return {"error": str(e)}


if __name__ == "__main__":
    results = main()
    if "summary" in results:
        print("\n=== Tool 정확도 평가 요약 ===")
        summary = results["summary"]
        print(f"평가 질문 수: {summary['total_evaluated']}")
        print(f"Tool 선택 정확도: {summary['tool_selection_accuracy']['mean']:.1%} (±{summary['tool_selection_accuracy']['std']:.1%})")
        print(f"파라미터 정확도: {summary['parameter_accuracy']['mean']:.1%} (±{summary['parameter_accuracy']['std']:.1%})")
        print(f"종합 정확도: {summary['combined_accuracy']['mean']:.1%}")

        if "by_category" in results:
            print("\n카테고리별 정확도:")
            for category, stats in results["by_category"].items():
                print(f"  {category}: 선택 {stats['selection_accuracy']:.1%}, 파라미터 {stats['parameter_accuracy']:.1%} (n={stats['count']})")
