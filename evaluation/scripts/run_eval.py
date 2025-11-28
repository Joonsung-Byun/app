"""
단일 패스로 질문별 Agent 호출을 실행하고 원시 로그를 수집합니다.
- 모델 응답, intermediate_steps, latency, 메모리, tool_timings 포함
"""

import asyncio
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
from backend.utils.tool_timings import get_and_reset as get_tool_timings, clear_tool_timings, enable_tool_timing, disable_tool_timing


def serialize_response(raw_response):
    """LangChain 응답 객체를 JSON 직렬화 가능한 dict로 변환"""
    if not isinstance(raw_response, dict):
        return {"output": raw_response, "intermediate_steps": []}

    steps = raw_response.get("intermediate_steps") or []
    serialized_steps = []
    for step in steps:
        if not step:
            continue
        if isinstance(step, dict):
            serialized_steps.append(step)
            continue
        if len(step) < 2:
            continue
        action, observation = step[0], step[1]
        obs_serialized = observation
        if isinstance(observation, (dict, list, str, int, float, bool)) or observation is None:
            obs_serialized = observation
        else:
            obs_serialized = str(observation)

        tool_input = getattr(action, "tool_input", None)
        if not isinstance(tool_input, (dict, list, str, int, float, bool)) and tool_input is not None:
            tool_input = {"raw": str(tool_input)}

        serialized_steps.append({
            "tool": getattr(action, "tool", None),
            "tool_input": tool_input,
            "log": getattr(action, "log", None),
            "observation": obs_serialized,
        })

    data = dict(raw_response)
    data["intermediate_steps"] = serialized_steps
    return data


async def _ainvoke(agent, payload: Dict[str, Any]):
    return await agent.ainvoke(payload)


def run_agent_once(agent, item: Dict[str, Any], conversation_id: str, chat_history=None) -> Dict[str, Any]:
    chat_history = chat_history or []
    mem_before = psutil.Process().memory_info().rss / 1024 / 1024
    start = time.time()
    error = None
    response = None
    enable_tool_timing()
    try:
        payload = {
            "input": item["question"],
            "conversation_id": conversation_id,
            "chat_history": chat_history
        }
        raw_response = asyncio.run(_ainvoke(agent, payload))
        response = serialize_response(raw_response)
    except Exception as e:
        error = str(e)
    finally:
        tool_timings = get_tool_timings()
        disable_tool_timing()

    latency = time.time() - start
    mem_after = psutil.Process().memory_info().rss / 1024 / 1024

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


def run_all(agent, sample: int = None, question_ids: List[int] | None = None) -> Dict[str, Any]:
    data = load_dataset()
    questions: List[Dict[str, Any]] = data["questions"]
    if question_ids:
        id_set = set(question_ids)
        questions = [q for q in questions if q.get("id") in id_set]
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
    parser.add_argument("--question-id", type=int, action="append", help="특정 질문 ID만 실행 (여러 개 지정 가능)")
    args = parser.parse_args()
    result = run_all(agent, sample=args.sample, question_ids=args.question_id)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"✅ 러너 완료: {out_path}")


if __name__ == "__main__":
    main()
