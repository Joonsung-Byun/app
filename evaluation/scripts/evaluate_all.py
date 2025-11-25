"""
전체 평가 실행 스크립트
모든 평가를 순차적으로 실행하고 종합 리포트 생성
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# 프로젝트 루트/백엔드 경로 추가
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))  # evaluation.* import 가능
sys.path.insert(0, str(ROOT_DIR / "backend"))

from evaluation.scripts.evaluate_answer import evaluate_answer_quality
from evaluation.scripts.evaluate_tools import evaluate_tool_accuracy, ToolCallLogger
from evaluation.scripts.evaluate_system import evaluate_system_performance
from evaluation.scripts.eval_cases import load_dataset, partition_by_case


def run_all_evaluations(
    output_dir: str = None,
    skip_rag: bool = False,
    skip_answer: bool = False,
    skip_tools: bool = False,
    skip_system: bool = False,
    sample_size: int = None,
    system_sample: int = 20
):
    """모든 평가 실행"""

    # 출력 디렉토리 설정
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path(__file__).parent.parent / "results"

    output_path.mkdir(parents=True, exist_ok=True)

    # 테스트 데이터 로드
    data = load_dataset()
    test_questions = data["questions"]
    meta = data.get("metadata", {})

    # 샘플 크기 적용
    if sample_size and sample_size < len(test_questions):
        import random
        test_questions = random.sample(test_questions, sample_size)
        print(f"📊 샘플 크기: {sample_size}개 질문\n")

    # Agent 초기화
    try:
        from agent.agent import create_agent
        agent = create_agent()
    except ImportError as e:
        print(f"❌ Agent 임포트 실패: {e}")
        return {"error": str(e)}

    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(test_questions),
            "sample_size": sample_size
        }
    }

    # 1. RAG 평가 (Case2 대상)
    if not skip_rag:
        try:
            from evaluation.scripts.evaluate_rag import evaluate_rag_quality, _build_retriever
            print("=" * 50)
            print("1. RAG 검색 품질 평가")
            print("=" * 50)
            retriever = _build_retriever()
            if retriever:
                case2_questions = [
                    q for q in test_questions
                    if "search_facilities" in (q.get("expected_tools") or [])
                    and q.get("relevant_doc_ids")
                ]
                print(f"RAG 평가 대상 문항: {len(case2_questions)}개")
                rag_results = evaluate_rag_quality(retriever, case2_questions, k=3)
                results["rag"] = rag_results
                with open(output_path / "rag_evaluation.json", "w", encoding="utf-8") as f:
                    json.dump(rag_results, f, ensure_ascii=False, indent=2)
                print(f"✅ RAG 평가 완료: {len(case2_questions)}개 문항\n")
            else:
                results["rag"] = {"skipped": True, "reason": "retriever unavailable"}
                print("⚠️ RAG retriever를 구성하지 못해 스킵되었습니다.\n")
            print()
        except Exception as e:
            results["rag"] = {"error": str(e)}
            print(f"⚠️ RAG 평가 실패: {e}\n")

    # 2. 답변 품질 평가
    if not skip_answer:
        print("=" * 50)
        print("2. 답변 품질 평가 (LLM-as-Judge)")
        print("=" * 50)
        answer_results = evaluate_answer_quality(agent, test_questions)
        results["answer_quality"] = answer_results

        # 개별 결과 저장
        with open(output_path / "answer_evaluation.json", "w", encoding="utf-8") as f:
            json.dump(answer_results, f, ensure_ascii=False, indent=2)
        print()

    # 3. Tool 정확도 평가
    if not skip_tools:
        print("=" * 50)
        print("3. Tool 사용 정확도 평가")
        print("=" * 50)
        tool_logger = ToolCallLogger()
        tool_results = evaluate_tool_accuracy(agent, test_questions, tool_logger, meta=meta)
        results["tool_accuracy"] = tool_results
        if "service_quality" in tool_results:
            results["service_quality"] = tool_results["service_quality"]

        # 개별 결과 저장
        with open(output_path / "tool_evaluation.json", "w", encoding="utf-8") as f:
            json.dump(tool_results, f, ensure_ascii=False, indent=2)
        print()

    # 4. 시스템 성능 평가
    if not skip_system:
        print("=" * 50)
        print("4. 시스템 성능 평가")
        print("=" * 50)
        sys_sample = system_sample if system_sample and system_sample > 0 else None
        system_results = evaluate_system_performance(agent, test_questions, sample_size=sys_sample)
        results["system_performance"] = system_results

        # 개별 결과 저장
        with open(output_path / "system_evaluation.json", "w", encoding="utf-8") as f:
            json.dump(system_results, f, ensure_ascii=False, indent=2)
        print()

    # 종합 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_output = output_path / f"evaluation_report_{timestamp}.json"
    with open(combined_output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 마크다운 리포트 생성
    generate_markdown_report(results, output_path / f"evaluation_report_{timestamp}.md")

    print("=" * 50)
    print(f"✅ 평가 완료!")
    print(f"   JSON 리포트: {combined_output}")
    print(f"   MD 리포트: {output_path / f'evaluation_report_{timestamp}.md'}")
    print("=" * 50)

    return results


def generate_markdown_report(results: dict, output_path: Path):
    """마크다운 형식의 리포트 생성"""

    md = []
    md.append("# 성능 평가 리포트\n")
    md.append(f"**평가 일시**: {results['metadata']['timestamp']}\n")
    md.append(f"**평가 질문 수**: {results['metadata']['total_questions']}\n")
    md.append("---\n")

    # 답변 품질
    if "answer_quality" in results and "summary" in results["answer_quality"]:
        summary = results["answer_quality"]["summary"]
        md.append("## 1. 답변 품질 (LLM-as-Judge)\n")
        md.append("| 항목 | 평균 | 표준편차 | 최소 | 최대 |")
        md.append("|------|------|----------|------|------|")
        md.append(f"| 정확성 | {summary['accuracy']['mean']:.2f} | {summary['accuracy']['std']:.2f} | {summary['accuracy']['min']:.0f} | {summary['accuracy']['max']:.0f} |")
        md.append(f"| 관련성 | {summary['relevance']['mean']:.2f} | {summary['relevance']['std']:.2f} | {summary['relevance']['min']:.0f} | {summary['relevance']['max']:.0f} |")
        md.append(f"| 유용성 | {summary['usefulness']['mean']:.2f} | {summary['usefulness']['std']:.2f} | {summary['usefulness']['min']:.0f} | {summary['usefulness']['max']:.0f} |")
        md.append(f"| **종합** | **{summary['overall']['mean']:.2f}** | {summary['overall']['std']:.2f} | {summary['overall']['min']:.0f} | {summary['overall']['max']:.0f} |")
        md.append("\n")

    # Tool 정확도
    if "tool_accuracy" in results and "summary" in results["tool_accuracy"]:
        summary = results["tool_accuracy"]["summary"]
        md.append("## 2. Tool 사용 정확도\n")
        md.append(f"- **Tool 선택 정확도**: {summary['tool_selection_accuracy']['mean']:.1%}")
        md.append(f"- **파라미터 정확도**: {summary['parameter_accuracy']['mean']:.1%}")
        md.append(f"- **종합 정확도**: {summary['combined_accuracy']['mean']:.1%}")
        md.append("\n")

        if "by_category" in results["tool_accuracy"]:
            md.append("### 카테고리별 정확도\n")
            md.append("| 카테고리 | 질문 수 | Tool 선택 | 파라미터 |")
            md.append("|----------|---------|-----------|----------|")
            for cat, stats in results["tool_accuracy"]["by_category"].items():
                md.append(f"| {cat} | {stats['count']} | {stats['selection_accuracy']:.1%} | {stats['parameter_accuracy']:.1%} |")
            md.append("\n")
        if "by_tool" in results["tool_accuracy"]:
            md.append("### 툴별 호출 성공률\n")
            md.append("| 툴 | 기대 호출 | 실제 호출(히트) | 성공률 |")
            md.append("|----|----------|---------------|--------|")
            for tool, stats in results["tool_accuracy"]["by_tool"].items():
                md.append(f"| {tool} | {stats.get('expected',0)} | {stats.get('hit',0)} | {stats.get('success_rate',0):.1%} |")
            md.append("\n")

    # 서비스 품질 요약 (케이스별 성공률)
    if "service_quality" in results and "by_case" in results["service_quality"]:
        md.append("## 3. 서비스 품질 (케이스별)\n")
        md.append("| 케이스 | 성공률 | 샘플 수 | 지표 설명 |")
        md.append("|--------|--------|---------|-----------|")
        for case, stats in results["service_quality"]["by_case"].items():
            desc = stats.get("description", "")
            md.append(f"| {case} | {stats.get('success_rate',0):.1%} | {stats.get('count',0)} | {desc} |")
        md.append("\n")

    # RAG 검색 품질
    if "rag" in results and "summary" in results["rag"]:
        summary = results["rag"]["summary"]
        md.append("## 4. RAG 검색 품질\n")
        md.append(f"- Precision@{summary['k']}: {summary['precision_at_k']['mean']:.3f}")
        md.append(f"- MRR: {summary['mrr']['mean']:.3f}")
        md.append("\n")

    # 시스템 성능
    if "system_performance" in results and "summary" in results["system_performance"]:
        summary = results["system_performance"]["summary"]
        md.append("## 5. 시스템 성능\n")
        md.append("### 응답 시간\n")
        md.append(f"- 평균: **{summary['latency']['mean']:.2f}s** (±{summary['latency']['std']:.2f}s)")
        md.append(f"- P50: {summary['latency']['p50']:.2f}s")
        md.append(f"- P90: {summary['latency']['p90']:.2f}s")
        md.append(f"- P99: {summary['latency']['p99']:.2f}s")
        md.append("\n### 메모리\n")
        md.append(f"- 초기: {summary['memory']['initial_mb']:.1f} MB")
        md.append(f"- 최종: {summary['memory']['final_mb']:.1f} MB")
        md.append(f"- 피크: {summary['memory']['peak_mb']:.1f} MB")
        md.append(f"\n### 성공률: **{summary['success_rate']:.1%}** ({summary['total_successes']}/{summary['total_evaluated']})\n")

    # 파일 저장
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


def main():
    parser = argparse.ArgumentParser(description="Kids Chatbot 성능 평가")
    parser.add_argument("--output", "-o", type=str, help="결과 저장 디렉토리")
    parser.add_argument("--sample", "-s", type=int, help="샘플 크기 (전체 평가 대신 일부만)")
    parser.add_argument("--skip-rag", action="store_true", help="RAG 평가 스킵")
    parser.add_argument("--skip-answer", action="store_true", help="답변 품질 평가 스킵")
    parser.add_argument("--skip-tools", action="store_true", help="Tool 정확도 평가 스킵")
    parser.add_argument("--skip-system", action="store_true", help="시스템 성능 평가 스킵")
    parser.add_argument("--system-sample", type=int, default=20, help="시스템 성능 평가 샘플 크기 (기본 20, 0/음수면 전체)")

    args = parser.parse_args()

    run_all_evaluations(
        output_dir=args.output,
        skip_rag=args.skip_rag,
        skip_answer=args.skip_answer,
        skip_tools=args.skip_tools,
        skip_system=args.skip_system,
        sample_size=args.sample,
        system_sample=args.system_sample
    )


if __name__ == "__main__":
    main()
