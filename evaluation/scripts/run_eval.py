"""
단일 패스로 질문별 Agent 호출을 실행하고 원시 로그를 수집합니다.
- 모델 응답, intermediate_steps, latency, 메모리, tool_timings 포함
"""

import json
import time
import psutil
from pathlib import Path
from typing import List, Dict, Any
import sys
import random

# 경로 설정
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from evaluation.scripts.eval_cases import load_dataset
from backend.utils.tool_timings import get_and_reset as get_tool_timings


def run_agent_once(agent, item: Dict[str, Any], conversation_id: str, chat_history=None) -> Dict[str, Any]:
    chat_history = chat_history or []
    mem_before = psutil.Process().memory_info().rss / 1024 / 1024
    start = time.time()
    error = None
    response = None
    try:
        response = agent.invoke({
            "input": item["question"],
            "conversation_id": conversation_id,
            "chat_history": chat_history
        })
    except Exception as e:
        error = str(e)
    latency = time.time() - start
    mem_after = psutil.Process().memory_info().rss / 1024 / 1024
    tool_timings = get_tool_timings()
    return {
        "conversation_id": conversation_id,
        "question": item["question"],
        "item": item,
        "response": response,
        "error": error,
        "latency": latency,
        "memory_before": mem_before,
        "memory_after": mem_after,
        "tool_timings": tool_timings
    }


def run_all(agent, sample: int = None) -> Dict[str, Any]:
    data = load_dataset()
    questions: List[Dict[str, Any]] = data["questions"]
    if sample and sample > 0 and sample < len(questions):
        questions = random.sample(questions, sample)
    runs = []
    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] running: {q['question'][:40]}...")
        conv_id = f"eval_{i}"
        runs.append(run_agent_once(agent, q, conv_id))
    return {"runs": runs, "metadata": data.get("metadata", {}), "questions": questions}


def main():
    from agent.agent import create_agent
    agent = create_agent()
    import argparse
    parser = argparse.ArgumentParser(description="단일 패스 러너")
    parser.add_argument("--sample", "-s", type=int, help="샘플 크기")
    parser.add_argument("--output", "-o", type=str, default="evaluation/results/raw_runs.json")
    args = parser.parse_args()
    result = run_all(agent, sample=args.sample)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"✅ 러너 완료: {out_path}")


if __name__ == "__main__":
    main()
