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

# 백엔드 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from evaluate_answer import evaluate_answer_quality
from evaluate_tools import evaluate_tool_accuracy, ToolCallLogger
from evaluate_system import evaluate_system_performance


def run_all_evaluations(
    output_dir: str = None,
    skip_rag: bool = False,
    skip_answer: bool = False,
    skip_tools: bool = False,
    skip_system: bool = False,
    sample_size: int = None
):
    """모든 평가 실행"""

    # 출력 디렉토리 설정
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path(__file__).parent.parent / "results"

    output_path.mkdir(parents=True, exist_ok=True)

    # 테스트 데이터 로드
    dataset_path = Path(__file__).parent.parent / "datasets" / "test_questions.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_questions = data["questions"]

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

    # 1. RAG 평가 (현재 스킵 - relevant_doc_ids 필요)
    if not skip_rag:
        print("=" * 50)
        print("1. RAG 검색 품질 평가")
        print("=" * 50)
        print("⚠️ RAG 평가는 relevant_doc_ids가 필요합니다. 스킵됩니다.\n")
        results["rag"] = {"skipped": True, "reason": "relevant_doc_ids not set"}

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
        tool_results = evaluate_tool_accuracy(agent, test_questions, tool_logger)
        results["tool_accuracy"] = tool_results

        # 개별 결과 저장
        with open(output_path / "tool_evaluation.json", "w", encoding="utf-8") as f:
            json.dump(tool_results, f, ensure_ascii=False, indent=2)
        print()

    # 4. 시스템 성능 평가
    if not skip_system:
        print("=" * 50)
        print("4. 시스템 성능 평가")
        print("=" * 50)
        system_results = evaluate_system_performance(agent, test_questions)
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

    # 시스템 성능
    if "system_performance" in results and "summary" in results["system_performance"]:
        summary = results["system_performance"]["summary"]
        md.append("## 3. 시스템 성능\n")
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

    args = parser.parse_args()

    run_all_evaluations(
        output_dir=args.output,
        skip_rag=args.skip_rag,
        skip_answer=args.skip_answer,
        skip_tools=args.skip_tools,
        skip_system=args.skip_system,
        sample_size=args.sample
    )


if __name__ == "__main__":
    main()
