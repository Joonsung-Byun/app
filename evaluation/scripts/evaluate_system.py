"""
시스템 성능 평가 스크립트
- 응답 시간
- 메모리 사용량
- 성공률
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import time
import random

# 백엔드 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import psutil
import numpy as np
from evaluation.scripts.eval_cases import classify_case
from backend.utils.tool_timings import get_and_reset as get_tool_timings


def measure_response_time(agent, question: str) -> Dict[str, Any]:
    """응답 시간 측정"""
    start_time = time.time()
    success = False
    error_message = None
    response = None

    try:
        response = agent.invoke({
            "input": question,
            "conversation_id": "eval_session",
            "chat_history": []
        })
        success = True
    except Exception as e:
        error_message = str(e)

    end_time = time.time()
    latency = end_time - start_time

    return {
        "latency": latency,
        "success": success,
        "error": error_message,
        "response": response
    }


def get_memory_usage() -> float:
    """현재 프로세스 메모리 사용량 (MB)"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def evaluate_system_performance(
    agent,
    test_data: List[Dict[str, Any]],
    warmup_questions: int = 3,
    sample_size: int = None,
    meta: Dict[str, Any] = None,
    case_weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """시스템 성능 전체 평가"""
    meta = meta or {}

    # 샘플링 (빠른 성능 측정을 위해)
    if sample_size and sample_size > 0 and sample_size < len(test_data):
        test_data = random.sample(test_data, sample_size)
        print(f"📊 시스템 성능 샘플 평가: {len(test_data)}개 질문 사용\n")

    # 타이밍 기록 초기화
    get_tool_timings()

    # 워밍업 (첫 몇 개 질문으로 캐시/초기화)
    print(f"워밍업 중... ({warmup_questions}개 질문)")
    for i in range(min(warmup_questions, len(test_data))):
        try:
            agent.invoke({
                "input": test_data[i]["question"],
                "conversation_id": "eval_warmup",
                "chat_history": []
            })
        except:
            pass
        time.sleep(0.5)

    latencies = []
    memory_usage = []
    successes = []
    results = []
    by_case_latencies = {}
    conv_case_map = {}

    initial_memory = get_memory_usage()
    print(f"초기 메모리: {initial_memory:.1f} MB\n")

    for i, item in enumerate(test_data):
        question = item["question"]
        category = item.get("category", "unknown")
        ctype = classify_case(item, meta)
        conv_id = f"eval_system_{i}"
        conv_case_map[conv_id] = ctype

        print(f"[{i+1}/{len(test_data)}] 테스트 중: {question[:30]}...")

        # 메모리 측정 (before)
        mem_before = get_memory_usage()

        # 응답 시간 측정
        start_time = time.time()
        try:
            response = agent.invoke({
                "input": question,
                "conversation_id": conv_id,
                "chat_history": []
            })
            success = True
            error_message = None
        except Exception as e:
            success = False
            error_message = str(e)
        latency = time.time() - start_time
        result = {
            "latency": latency,
            "success": success,
            "error": error_message,
            "response": None
        }

        # 메모리 측정 (after)
        mem_after = get_memory_usage()

        latencies.append(result["latency"])
        memory_usage.append(mem_after)
        successes.append(result["success"])

        results.append({
            "question": question,
            "category": category,
            "case": ctype,
            "latency": result["latency"],
            "memory_before": mem_before,
            "memory_after": mem_after,
            "memory_delta": mem_after - mem_before,
            "success": result["success"],
            "error": result["error"]
        })

        # 케이스별 기록
        if ctype not in by_case_latencies:
            by_case_latencies[ctype] = []
        by_case_latencies[ctype].append(result["latency"])

        # Rate limiting
        time.sleep(0.3)

    final_memory = get_memory_usage()
    success_rate = sum(successes) / len(successes) if successes else 0

    # 케이스별 평균 및 가중 평균
    by_case_latency = {
        c: {
            "count": len(vals),
            "mean": float(np.mean(vals)),
            "p90": float(np.percentile(vals, 90)),
        }
        for c, vals in by_case_latencies.items()
    }
    weighted_latency = None
    if case_weights:
        total_w = sum(case_weights.values())
        if total_w > 0:
            weighted_latency = sum(
                case_weights.get(c, 0) / total_w * by_case_latency.get(c, {}).get("mean", 0)
                for c in case_weights.keys()
            )

    # 툴별 실행 시간 (백엔드 콜백 기록 활용)
    timing_records = get_tool_timings()
    per_tool_time = {}
    per_case_tool_time = {}
    if timing_records:
        from collections import defaultdict
        tmp = defaultdict(list)
        tmp_case = defaultdict(lambda: defaultdict(list))
        for rec in timing_records:
            tool_name = rec.get("tool", "unknown_tool")
            tmp[tool_name].append(rec.get("duration", 0))
            case = conv_case_map.get(rec.get("conversation_id"), "unknown")
            tmp_case[case][tool_name].append(rec.get("duration", 0))
        per_tool_time = {
            tool: {
                "count": len(times),
                "mean_s": float(np.mean(times)),
                "max_s": float(np.max(times)),
            }
            for tool, times in tmp.items()
        }
        per_case_tool_time = {
            case: {
                tool: {
                    "count": len(times),
                    "mean_s": float(np.mean(times)),
                    "max_s": float(np.max(times)),
                }
                for tool, times in tool_map.items()
            }
            for case, tool_map in tmp_case.items()
        }

    return {
        "summary": {
            "total_evaluated": len(test_data),
            "latency": {
                "mean": float(np.mean(latencies)),
                "std": float(np.std(latencies)),
                "min": float(np.min(latencies)),
                "max": float(np.max(latencies)),
                "p50": float(np.percentile(latencies, 50)),
                "p90": float(np.percentile(latencies, 90)),
                "p99": float(np.percentile(latencies, 99))
            },
            "memory": {
                "initial_mb": initial_memory,
                "final_mb": final_memory,
                "peak_mb": float(np.max(memory_usage)),
                "mean_mb": float(np.mean(memory_usage)),
                "growth_mb": final_memory - initial_memory
            },
            "success_rate": success_rate,
            "total_successes": sum(successes),
            "total_failures": len(successes) - sum(successes),
            "weighted_latency_mean": weighted_latency
        },
        "details": results,
        "by_category": calculate_category_performance(results),
        "by_case_latency": by_case_latency,
        "by_tool_time": per_tool_time,
        "by_case_tool_time": per_case_tool_time
    }


def evaluate_system_from_runs(
    runs: List[Dict[str, Any]],
    meta: Dict[str, Any],
    case_weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """러너에서 수집한 runs 기반으로 시스템 성능 집계"""
    latencies = []
    memory_usage = []
    successes = []
    results = []
    by_case_latencies = {}
    conv_case_map = {}

    for run in runs:
        qobj = run.get("item", {})
        ctype = classify_case(qobj, meta)
        conv_id = run.get("conversation_id")
        conv_case_map[conv_id] = ctype

        lat = run.get("latency", 0)
        latencies.append(lat)
        mem_after = run.get("memory_after", 0)
        memory_usage.append(mem_after)
        success = run.get("error") is None
        successes.append(success)
        results.append({
            "question": qobj.get("question"),
            "category": qobj.get("category", "unknown"),
            "case": ctype,
            "latency": lat,
            "memory_before": run.get("memory_before"),
            "memory_after": mem_after,
            "memory_delta": (mem_after - run.get("memory_before", mem_after)) if run.get("memory_before") is not None else 0,
            "success": success,
            "error": run.get("error")
        })
        by_case_latencies.setdefault(ctype, []).append(lat)

    final_memory = memory_usage[-1] if memory_usage else 0
    initial_memory = memory_usage[0] if memory_usage else 0
    success_rate = sum(successes) / len(successes) if successes else 0

    by_case_latency = {
        c: {
            "count": len(vals),
            "mean": float(np.mean(vals)),
            "p90": float(np.percentile(vals, 90)),
        }
        for c, vals in by_case_latencies.items()
    }
    weighted_latency = None
    if case_weights:
        total_w = sum(case_weights.values())
        if total_w > 0:
            weighted_latency = sum(
                case_weights.get(c, 0) / total_w * by_case_latency.get(c, {}).get("mean", 0)
                for c in case_weights.keys()
            )

    # 툴 타이밍: runs에 포함된 tool_timings 사용
    per_tool_time = {}
    per_case_tool_time = {}
    from collections import defaultdict
    tmp = defaultdict(list)
    tmp_case = defaultdict(lambda: defaultdict(list))
    for run in runs:
        conv_id = run.get("conversation_id")
        case = conv_case_map.get(conv_id, "unknown")
        for rec in run.get("tool_timings", []):
            tool_name = rec.get("tool", "unknown_tool")
            dur = rec.get("duration", 0)
            tmp[tool_name].append(dur)
            tmp_case[case][tool_name].append(dur)
    if tmp:
        per_tool_time = {
            tool: {
                "count": len(times),
                "mean_s": float(np.mean(times)),
                "max_s": float(np.max(times)),
            }
            for tool, times in tmp.items()
        }
    if tmp_case:
        per_case_tool_time = {
            case: {
                tool: {
                    "count": len(times),
                    "mean_s": float(np.mean(times)),
                    "max_s": float(np.max(times)),
                }
                for tool, times in tool_map.items()
            }
            for case, tool_map in tmp_case.items()
        }

    return {
        "summary": {
            "total_evaluated": len(latencies),
            "latency": {
                "mean": float(np.mean(latencies)) if latencies else 0.0,
                "std": float(np.std(latencies)) if latencies else 0.0,
                "min": float(np.min(latencies)) if latencies else 0.0,
                "max": float(np.max(latencies)) if latencies else 0.0,
                "p50": float(np.percentile(latencies, 50)) if latencies else 0.0,
                "p90": float(np.percentile(latencies, 90)) if latencies else 0.0,
                "p99": float(np.percentile(latencies, 99)) if latencies else 0.0
            },
            "memory": {
                "initial_mb": initial_memory,
                "final_mb": final_memory,
                "peak_mb": float(np.max(memory_usage)) if memory_usage else 0.0,
                "mean_mb": float(np.mean(memory_usage)) if memory_usage else 0.0,
                "growth_mb": final_memory - initial_memory
            },
            "success_rate": success_rate,
            "total_successes": sum(successes),
            "total_failures": len(successes) - sum(successes),
            "weighted_latency_mean": weighted_latency
        },
        "details": results,
        "by_category": calculate_category_performance(results),
        "by_case_latency": by_case_latency,
        "by_tool_time": per_tool_time,
        "by_case_tool_time": per_case_tool_time
    }


def calculate_category_performance(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """카테고리별 성능 통계"""
    categories = {}

    for result in results:
        category = result.get("category", "unknown")
        if category not in categories:
            categories[category] = {
                "latencies": [],
                "successes": []
            }

        categories[category]["latencies"].append(result["latency"])
        categories[category]["successes"].append(result["success"])

    stats = {}
    for category, data in categories.items():
        stats[category] = {
            "count": len(data["latencies"]),
            "avg_latency": float(np.mean(data["latencies"])),
            "success_rate": sum(data["successes"]) / len(data["successes"]) if data["successes"] else 0
        }

    return stats


def main():
    """시스템 성능 평가 실행"""
    import argparse
    parser = argparse.ArgumentParser(description="시스템 성능 평가")
    parser.add_argument("--sample", "-s", type=int, help="샘플 크기 (전체 대신 일부만)")
    parser.add_argument("--case-weights", type=str, help="케이스별 가중치 JSON 경로(예: {'case2':0.3,'web':0.2,...})")
    args = parser.parse_args()

    # 테스트 데이터 로드
    dataset_path = Path(__file__).parent.parent / "datasets" / "test_questions_prompt_pruned.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_questions = data["questions"]
    meta = data.get("metadata", {})

    case_weights = None
    if args.case_weights:
        try:
            with open(args.case_weights, "r", encoding="utf-8") as f:
                case_weights = json.load(f)
        except Exception as e:
            print(f"⚠️ 케이스 가중치 로드 실패: {e}")

    # Agent 초기화
    try:
        from agent.agent import create_agent
        agent = create_agent()

        results = evaluate_system_performance(agent, test_questions, sample_size=args.sample, meta=meta, case_weights=case_weights)

        # 결과 저장
        output_path = Path(__file__).parent.parent / "results" / "system_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 시스템 성능 평가 완료: {output_path}")
        return results

    except ImportError as e:
        print(f"⚠️ Agent 임포트 실패: {e}")
        print("백엔드의 agents 모듈 경로를 확인해주세요.")
        return {"error": str(e)}


if __name__ == "__main__":
    results = main()
    if "summary" in results:
        print("\n=== 시스템 성능 평가 요약 ===")
        summary = results["summary"]
        print(f"평가 질문 수: {summary['total_evaluated']}")
        print(f"\n응답 시간:")
        print(f"  평균: {summary['latency']['mean']:.2f}s (±{summary['latency']['std']:.2f}s)")
        print(f"  P50: {summary['latency']['p50']:.2f}s")
        print(f"  P90: {summary['latency']['p90']:.2f}s")
        print(f"  P99: {summary['latency']['p99']:.2f}s")
        print(f"  최소/최대: {summary['latency']['min']:.2f}s / {summary['latency']['max']:.2f}s")
        print(f"\n메모리:")
        print(f"  초기: {summary['memory']['initial_mb']:.1f} MB")
        print(f"  최종: {summary['memory']['final_mb']:.1f} MB")
        print(f"  피크: {summary['memory']['peak_mb']:.1f} MB")
        print(f"  증가량: {summary['memory']['growth_mb']:.1f} MB")
        print(f"\n성공률: {summary['success_rate']:.1%} ({summary['total_successes']}/{summary['total_evaluated']})")

        if "by_category" in results:
            print("\n카테고리별 성능:")
            for category, stats in results["by_category"].items():
                print(f"  {category}: {stats['avg_latency']:.2f}s, 성공률 {stats['success_rate']:.1%} (n={stats['count']})")
