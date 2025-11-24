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
    tool_logger: ToolCallLogger
) -> Dict[str, Any]:
    """Tool 사용 정확도 전체 평가"""

    selection_scores = []
    parameter_scores = []
    results = []

    for i, item in enumerate(test_data):
        question = item["question"]
        expected_tools = item.get("expected_tools", [])
        expected_params = item.get("expected_tool_params", {})

        print(f"[{i+1}/{len(test_data)}] 평가 중: {question[:30]}...")

        # 로거 리셋
        tool_logger.reset()

        # 에이전트 실행
        try:
            agent.invoke({
                "input": question,
                "conversation_id": "eval_session",
                "chat_history": []
            })
            actual_tools = tool_logger.get_called_tools()
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

        results.append({
            "question": question,
            "expected_tools": expected_tools,
            "actual_tools": actual_tools,
            "expected_params": expected_params,
            "actual_calls": actual_calls,
            "selection_accuracy": selection_score,
            "parameter_accuracy": parameter_score
        })

        # Rate limiting
        time.sleep(0.3)

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
        "by_category": calculate_category_stats(results, test_data)
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
    dataset_path = Path(__file__).parent.parent / "datasets" / "test_questions.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

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

        results = evaluate_tool_accuracy(agent, test_questions, tool_logger)

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
