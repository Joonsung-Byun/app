"""
RAG 검색 품질 평가 스크립트
- Precision@K
- Recall@K
- MRR (Mean Reciprocal Rank)
"""

import json
import sys
import os
from pathlib import Path

# 백엔드 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from typing import List, Dict, Any
import numpy as np


def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """검색된 K개 중 관련 문서 비율"""
    if not retrieved or not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)
    relevant_count = sum(1 for doc in retrieved_k if doc in relevant_set)

    return relevant_count / k


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """전체 관련 문서 중 검색된 비율"""
    if not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)
    relevant_count = sum(1 for doc in retrieved_k if doc in relevant_set)

    return relevant_count / len(relevant)


def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    """첫 정답 순위의 역수"""
    if not retrieved or not relevant:
        return 0.0

    relevant_set = set(relevant)
    for i, doc in enumerate(retrieved, 1):
        if doc in relevant_set:
            return 1.0 / i

    return 0.0


def evaluate_rag_quality(
    retriever,
    test_data: List[Dict[str, Any]],
    k: int = 5
) -> Dict[str, Any]:
    """RAG 검색 품질 전체 평가"""

    precisions = []
    recalls = []
    mrrs = []

    results = []

    for item in test_data:
        question = item["question"]
        relevant_docs = item.get("relevant_doc_ids", [])

        # 관련 문서 ID가 없으면 스킵
        if not relevant_docs:
            continue

        # 검색 수행
        try:
            retrieved_docs = retriever.get_relevant_documents(question)
            retrieved_ids = [doc.metadata.get("id", str(i)) for i, doc in enumerate(retrieved_docs)]
        except Exception as e:
            print(f"Error retrieving for question '{question}': {e}")
            continue

        # 메트릭 계산
        p_at_k = precision_at_k(retrieved_ids, relevant_docs, k)
        r_at_k = recall_at_k(retrieved_ids, relevant_docs, k)
        mrr = mean_reciprocal_rank(retrieved_ids, relevant_docs)

        precisions.append(p_at_k)
        recalls.append(r_at_k)
        mrrs.append(mrr)

        results.append({
            "question": question,
            "retrieved": retrieved_ids[:k],
            "relevant": relevant_docs,
            "precision_at_k": p_at_k,
            "recall_at_k": r_at_k,
            "mrr": mrr
        })

    if not precisions:
        return {
            "error": "No questions with relevant_doc_ids found",
            "note": "RAG 평가를 위해서는 test_questions.json의 relevant_doc_ids를 채워야 합니다."
        }

    return {
        "summary": {
            "total_evaluated": len(precisions),
            "precision_at_k": {
                "mean": float(np.mean(precisions)),
                "std": float(np.std(precisions)),
                "min": float(np.min(precisions)),
                "max": float(np.max(precisions))
            },
            "recall_at_k": {
                "mean": float(np.mean(recalls)),
                "std": float(np.std(recalls)),
                "min": float(np.min(recalls)),
                "max": float(np.max(recalls))
            },
            "mrr": {
                "mean": float(np.mean(mrrs)),
                "std": float(np.std(mrrs)),
                "min": float(np.min(mrrs)),
                "max": float(np.max(mrrs))
            },
            "k": k
        },
        "details": results
    }


def main():
    """RAG 평가 실행"""
    # 테스트 데이터 로드
    dataset_path = Path(__file__).parent.parent / "datasets" / "test_questions.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_questions = data["questions"]

    # RAG 관련 문서가 설정된 질문만 필터링
    rag_questions = [q for q in test_questions if q.get("relevant_doc_ids")]

    if not rag_questions:
        print("⚠️ RAG 평가를 위한 relevant_doc_ids가 설정된 질문이 없습니다.")
        print("test_questions.json의 relevant_doc_ids를 먼저 채워주세요.")
        return {
            "error": "No RAG test data available",
            "note": "relevant_doc_ids 필드를 채워주세요"
        }

    # Retriever 초기화 (백엔드에서 가져오기)
    try:
        from rag.retriever import get_retriever
        retriever = get_retriever()

        results = evaluate_rag_quality(retriever, rag_questions, k=5)

        # 결과 저장
        output_path = Path(__file__).parent.parent / "results" / "rag_evaluation.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"✅ RAG 평가 완료: {output_path}")
        return results

    except ImportError as e:
        print(f"⚠️ Retriever 임포트 실패: {e}")
        print("백엔드의 RAG 모듈 경로를 확인해주세요.")
        return {"error": str(e)}


if __name__ == "__main__":
    results = main()
    if "summary" in results:
        print("\n=== RAG 평가 요약 ===")
        summary = results["summary"]
        print(f"평가 질문 수: {summary['total_evaluated']}")
        print(f"Precision@{summary['k']}: {summary['precision_at_k']['mean']:.3f} (±{summary['precision_at_k']['std']:.3f})")
        print(f"Recall@{summary['k']}: {summary['recall_at_k']['mean']:.3f} (±{summary['recall_at_k']['std']:.3f})")
        print(f"MRR: {summary['mrr']['mean']:.3f} (±{summary['mrr']['std']:.3f})")
