"""
답변 품질 평가 스크립트 (LLM-as-Judge)
- GPT-4를 사용하여 정확성, 관련성, 유용성 평가
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import time

# 백엔드 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

# .env 파일 로드
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

EVALUATION_PROMPT = """당신은 어린이용 AI 챗봇의 답변 품질을 평가하는 전문가입니다.

다음 질문에 대한 AI의 답변을 평가해주세요.

## 질문
{question}

## 예상 정답 (참고용)
{ground_truth}

## AI 답변
{model_answer}

## 평가 기준 (각 1-5점)

1. **정확성**: 답변이 사실적으로 정확한가?
   - 5점: 완전히 정확
   - 3점: 대체로 정확하나 일부 오류
   - 1점: 심각한 오류 또는 잘못된 정보

2. **관련성**: 질문에 적절하게 답했는가?
   - 5점: 질문에 완벽히 부합
   - 3점: 대체로 관련 있으나 일부 불필요한 내용
   - 1점: 질문과 무관한 답변

3. **유용성**: 어린이에게 도움이 되는 답변인가?
   - 5점: 매우 이해하기 쉽고 유용
   - 3점: 이해 가능하나 개선 여지 있음
   - 1점: 어린이가 이해하기 어려움

## 응답 형식 (JSON)
```json
{{
  "accuracy": <1-5>,
  "relevance": <1-5>,
  "usefulness": <1-5>,
  "overall": <1-5>,
  "feedback": "<간단한 피드백>"
}}
```
"""


def evaluate_single_answer(
    client: OpenAI,
    question: str,
    ground_truth: str,
    model_answer: str
) -> Dict[str, Any]:
    """단일 답변 평가"""

    prompt = EVALUATION_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        model_answer=model_answer
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that evaluates AI responses. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        return {
            "error": str(e),
            "accuracy": 0,
            "relevance": 0,
            "usefulness": 0,
            "overall": 0,
            "feedback": f"평가 실패: {e}"
        }


def get_model_answer(agent, question: str) -> str:
    """챗봇에서 답변 가져오기"""
    try:
        response = agent.invoke({
            "input": question,
            "conversation_id": "eval_session",
            "chat_history": []
        })
        return response.get("output", str(response))
    except Exception as e:
        return f"Error: {e}"


def evaluate_answer_quality(
    agent,
    test_data: List[Dict[str, Any]],
    api_key: str = None
) -> Dict[str, Any]:
    """답변 품질 전체 평가"""

    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    accuracy_scores = []
    relevance_scores = []
    usefulness_scores = []
    overall_scores = []

    results = []

    for i, item in enumerate(test_data):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"[{i+1}/{len(test_data)}] 평가 중: {question[:30]}...")

        # 모델 답변 가져오기
        model_answer = get_model_answer(agent, question)

        # LLM-as-Judge로 평가
        evaluation = evaluate_single_answer(
            client, question, ground_truth, model_answer
        )

        if "error" not in evaluation:
            accuracy_scores.append(evaluation["accuracy"])
            relevance_scores.append(evaluation["relevance"])
            usefulness_scores.append(evaluation["usefulness"])
            overall_scores.append(evaluation["overall"])

        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "model_answer": model_answer,
            "evaluation": evaluation
        })

        # Rate limiting
        time.sleep(0.5)

    if not accuracy_scores:
        return {
            "error": "No successful evaluations",
            "details": results
        }

    return {
        "summary": {
            "total_evaluated": len(accuracy_scores),
            "accuracy": {
                "mean": float(np.mean(accuracy_scores)),
                "std": float(np.std(accuracy_scores)),
                "min": float(np.min(accuracy_scores)),
                "max": float(np.max(accuracy_scores))
            },
            "relevance": {
                "mean": float(np.mean(relevance_scores)),
                "std": float(np.std(relevance_scores)),
                "min": float(np.min(relevance_scores)),
                "max": float(np.max(relevance_scores))
            },
            "usefulness": {
                "mean": float(np.mean(usefulness_scores)),
                "std": float(np.std(usefulness_scores)),
                "min": float(np.min(usefulness_scores)),
                "max": float(np.max(usefulness_scores))
            },
            "overall": {
                "mean": float(np.mean(overall_scores)),
                "std": float(np.std(overall_scores)),
                "min": float(np.min(overall_scores)),
                "max": float(np.max(overall_scores))
            }
        },
        "details": results
    }


def main():
    """답변 품질 평가 실행"""
    # 테스트 데이터 로드
    dataset_path = Path(__file__).parent.parent / "datasets" / "test_questions.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_questions = data["questions"]

    # Agent 초기화 (백엔드에서 가져오기)
    try:
        from agent.agent import create_agent
        agent = create_agent()

        results = evaluate_answer_quality(agent, test_questions)

        # 결과 저장
        output_path = Path(__file__).parent.parent / "results" / "answer_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"✅ 답변 품질 평가 완료: {output_path}")
        return results

    except ImportError as e:
        print(f"⚠️ Agent 임포트 실패: {e}")
        print("백엔드의 agents 모듈 경로를 확인해주세요.")
        return {"error": str(e)}


if __name__ == "__main__":
    results = main()
    if "summary" in results:
        print("\n=== 답변 품질 평가 요약 ===")
        summary = results["summary"]
        print(f"평가 질문 수: {summary['total_evaluated']}")
        print(f"정확성: {summary['accuracy']['mean']:.2f}/5.0 (±{summary['accuracy']['std']:.2f})")
        print(f"관련성: {summary['relevance']['mean']:.2f}/5.0 (±{summary['relevance']['std']:.2f})")
        print(f"유용성: {summary['usefulness']['mean']:.2f}/5.0 (±{summary['usefulness']['std']:.2f})")
        print(f"종합: {summary['overall']['mean']:.2f}/5.0 (±{summary['overall']['std']:.2f})")
