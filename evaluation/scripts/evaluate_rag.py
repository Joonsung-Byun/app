"""
RAG 검색 품질 평가 스크립트
- Precision@K
- Recall@K
- MRR (Mean Reciprocal Rank)
"""

import json
import sys
import os
import argparse
import random
from pathlib import Path
import re

# 백엔드 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from typing import List, Dict, Any
import numpy as np
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.schema import Document

# 백엔드 설정/임베딩을 재사용하여 retriever를 직접 구성 (backend 코드는 수정하지 않음)
try:
    from config import settings
    from models.pca_embeddings import pca_embeddings
except Exception:
    settings = None
    pca_embeddings = None


def _build_retriever():
    """ChromaDB + pca_embeddings를 사용한 간단한 retriever 구성"""
    if not settings or not pca_embeddings:
        print("❌ retriever 구성 실패: settings 또는 pca_embeddings 로드 불가")
        return None

    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name="kid_program_collection")
    except Exception as e:
        print(f"❌ ChromaDB 연결 실패: {e}")
        return None

    class SimpleRetriever:
        def get_relevant_documents(self, query: str, n_results: int = 50):
            embedding = pca_embeddings.embed_query(query)
            results = collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["metadatas", "documents"],
            )
            docs = []
            ids = results.get("ids", [[]])[0] if results.get("ids") else []
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            documents = results.get("documents", [[]])[0] if results.get("documents") else []
            for i, doc_id in enumerate(ids):
                metadata = metadatas[i] if i < len(metadatas) else {}
                metadata = dict(metadata or {})
                metadata["id"] = doc_id
                text = documents[i] if i < len(documents) else ""
                docs.append(Document(page_content=text, metadata=metadata))
            return docs

    return SimpleRetriever()


def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """검색된 K개 중 관련 문서 비율"""
    if not retrieved or not relevant:
        return 0.0

    # 정규화 후 정확히 일치할 때만 매칭 (부분 문자열 매칭으로 잘못 카운트되는 경우 방지)
    def norm(s: str) -> str:
        return re.sub(r"[\s\W]+", "", str(s).lower())

    def is_match(a: str, b: str) -> bool:
        return norm(a) == norm(b)

    relevant_norm = [norm(x) for x in relevant]
    hits = 0
    for doc in retrieved[:k]:
        d = norm(doc)
        if any(is_match(d, r) for r in relevant_norm):
            hits += 1
    return hits / k


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """전체 관련 문서 중 검색된 비율"""
    if not relevant:
        return 0.0

    def norm(s: str) -> str:
        return re.sub(r"[\s\W]+", "", str(s).lower())

    def is_match(a: str, b: str) -> bool:
        return norm(a) == norm(b)

    relevant_norm = [norm(x) for x in relevant]
    matched = set()

    for doc in retrieved[:k]:
        d = norm(doc)
        for idx, r in enumerate(relevant_norm):
            if idx in matched:
                continue
            if is_match(d, r):
                matched.add(idx)
                break

    return len(matched) / len(relevant_norm) if relevant_norm else 0.0


def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    """첫 정답 순위의 역수"""
    if not retrieved or not relevant:
        return 0.0

    def norm(s: str) -> str:
        return re.sub(r"[\s\W]+", "", str(s).lower())

    def is_match(a: str, b: str) -> bool:
        return norm(a) == norm(b)

    relevant_norm = [norm(x) for x in relevant]
    for i, doc in enumerate(retrieved, 1):
        d = norm(doc)
        if any(is_match(d, r) for r in relevant_norm):
            return 1.0 / i
    return 0.0


def evaluate_rag_quality(
    retriever,
    test_data: List[Dict[str, Any]],
    k_precision: int = 3,
    k_recall: int = 20,
    n_results: int = 50
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
            retrieved_docs = retriever.get_relevant_documents(question, n_results=n_results)

            # Name을 우선 식별자로 사용하고, 없을 경우 id/순번 사용
            retrieved_ids = []
            for i, doc in enumerate(retrieved_docs):
                md = doc.metadata or {}
                name_candidate = md.get("Name") or md.get("name")
                id_candidate = md.get("id") or md.get("Id") or md.get("ID")
                identifier = name_candidate or id_candidate or str(i)
                retrieved_ids.append(str(identifier))
        except Exception as e:
            print(f"Error retrieving for question '{question}': {e}")
            continue

        # 메트릭 계산 (대소문자/공백 무시)
        norm_retrieved = [str(x).strip().lower() for x in retrieved_ids]
        norm_relevant = [str(x).strip().lower() for x in relevant_docs]

        p_at_k = precision_at_k(norm_retrieved, norm_relevant, k_precision)
        r_at_k = recall_at_k(norm_retrieved, norm_relevant, k_recall)
        mrr = mean_reciprocal_rank(norm_retrieved, norm_relevant[:k_precision])

        precisions.append(p_at_k)
        recalls.append(r_at_k)
        mrrs.append(mrr)

        results.append({
            "question": question,
            "retrieved": retrieved_ids[:k_recall],
            "relevant": relevant_docs,
            "precision_at_k": p_at_k,
            "recall_at_k": r_at_k,
            "mrr": mrr
        })

    if not precisions:
        return {
            "error": "No questions with relevant_doc_ids found",
            "note": "RAG 평가를 위해서는 test_questions_updated.json의 relevant_doc_ids를 채워야 합니다."
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
            "k_precision": k_precision,
            "k_recall": k_recall
        },
        "details": results
    }


def main():
    """RAG 평가 실행"""
    parser = argparse.ArgumentParser(description="RAG 검색 품질 평가")
    parser.add_argument("--sample", "-s", type=int, help="평가할 샘플 개수 (relevant_doc_ids가 있는 질문 중 랜덤)")
    parser.add_argument("--k-precision", type=int, default=3, help="Precision@K에 사용할 K (default: 3)")
    parser.add_argument("--k-recall", type=int, default=20, help="Recall@K에 사용할 K (default: 20)")
    parser.add_argument("--n-results", type=int, default=50, help="retriever에서 가져올 결과 수 (default: 50)")
    args = parser.parse_args()

    # 테스트 데이터 로드
    dataset_path = Path(__file__).parent.parent / "datasets" / "test_questions_prompt_pruned.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_questions = data["questions"]

    # RAG 관련 문서가 설정된 질문만 필터링
    rag_questions = [q for q in test_questions if q.get("relevant_doc_ids")]

    # 샘플링
    if args.sample and len(rag_questions) > args.sample:
        rag_questions = random.sample(rag_questions, args.sample)
        print(f"📊 샘플 평가: {len(rag_questions)}개 질문 사용")

    if not rag_questions:
        print("⚠️ RAG 평가를 위한 relevant_doc_ids가 설정된 질문이 없습니다.")
        print("test_questions_prompt_pruned.json의 relevant_doc_ids를 먼저 채워주세요.")
        return {
            "error": "No RAG test data available",
            "note": "relevant_doc_ids 필드를 채워주세요"
        }

    # 평가에서 직접 retriever를 구성 (backend 코드 수정 없음)
    retriever = _build_retriever()
    if retriever is None:
        return {
            "error": "Retriever unavailable",
            "note": "settings/pca_embeddings 로드 또는 Chroma 연결 실패"
        }

    results = evaluate_rag_quality(
        retriever,
        rag_questions,
        k_precision=args.k_precision,
        k_recall=args.k_recall,
        n_results=args.n_results
    )

    # 결과 저장
    output_path = Path(__file__).parent.parent / "results" / "rag_evaluation.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ RAG 평가 완료: {output_path}")
    return results


if __name__ == "__main__":
    results = main()
    if "summary" in results:
        print("\n=== RAG 평가 요약 ===")
        summary = results["summary"]
        print(f"평가 질문 수: {summary['total_evaluated']}")
        print(f"Precision@{summary['k_precision']}: {summary['precision_at_k']['mean']:.3f} (±{summary['precision_at_k']['std']:.3f})")
        print(f"Recall@{summary['k_recall']}: {summary['recall_at_k']['mean']:.3f} (±{summary['recall_at_k']['std']:.3f})")
        print(f"MRR: {summary['mrr']['mean']:.3f} (±{summary['mrr']['std']:.3f})")
