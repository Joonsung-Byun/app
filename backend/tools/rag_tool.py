from langchain.tools import tool
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from models.pca_embeddings import pca_embeddings
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

# ChromaDB 클라이언트 초기화
try:
    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(
            anonymized_telemetry=False
        )
    )
    print(settings.CHROMA_PORT,"chroma_port")
    print(settings.CHROMA_HOST,"chroma_host")
    collection = chroma_client.get_collection(
        name="kid_program_collection"
    )
    print(collection)
    
    logger.info(f"✅ ChromaDB 연결 성공: {collection.name}")
    logger.info(f"컬렉션 항목 수: {collection.count()}")
    
except Exception as e:
    logger.error(f"❌ ChromaDB 연결 실패: {e}")
    collection = None

@tool
def search_facilities(
    original_query: str,
    k: int = 5
) -> str:
    """
    사용자 질문과 가장 유사한 시설을 검색합니다.
    
    Args:
        original_query: 사용자의 원본 질문 (예: "부산 자전거 타기 좋은 곳", "서울 실내 놀이터")
        k: 반환할 결과 개수 (기본값: 10)
    
    Returns:
        시설 정보 JSON (유사도 높은 순으로 정렬)
    """
    logger.info(f"\n{'='*50}")
    logger.info(f"시설 검색 시작")
    logger.info(f"original_query: {original_query}, k: {k}")
    logger.info(f"{'='*50}")
    
    if collection is None:
        logger.error("ChromaDB 컬렉션이 없음")
        return json.dumps({
            "success": False,
            "message": "ChromaDB 연결 실패",
            "facilities": []
        }, ensure_ascii=False)
    
    # 쿼리 텍스트는 사용자 질문 그대로 사용
    query_text = original_query
    
    print(f"쿼리 텍스트: {query_text}")
    
    try:
        # 임베딩 생성
        print("임베딩 생성 중...")
        query_embedding = pca_embeddings.embed_query(query_text)
        print(f"✅ 임베딩 완료: {len(query_embedding)}차원")
        
        # 벡터 검색
        print("ChromaDB 벡터 검색 중...")
        print(f"✅ 임베딩 완료: {len(query_embedding)}차원")
        
        # 벡터 검색
        print("ChromaDB 벡터 검색 중...")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["metadatas", "documents", "distances"]
        )

        print(f"results: {results}")
        
        logger.info(f"✅ 벡터 검색 완료: {len(results['ids'][0])}개")
        
        facilities = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            distances = results['distances'][0]
            
            # 유사도 높은 순으로 상위 k개 반환
            for i, metadata in enumerate(metadatas):
                name = metadata.get("Name", metadata.get("name", "이름없음"))
                
                logger.info(f"  ✅ [{i+1}] {name} (distance: {distances[i]:.4f})")
                
                # 좌표
                lat = metadata.get("LAT", "37.5665")
                lon = metadata.get("LON", "126.9780")
                
                try:
                    lat = float(lat)
                    lon = float(lon)
                except (ValueError, TypeError):
                    lat = 37.5665
                    lon = 126.9780
                
                # 설명
                address = metadata.get("Address", "")
                category1 = metadata.get("Category1", "")
                category3 = metadata.get("Category3", "")
                
                desc = ""
                if i < len(documents) and documents[i]:
                    desc = documents[i][:100]
                elif address:
                    desc = address[:100]
                elif category3:
                    desc = f"{category1} - {category3}"
                
                facilities.append({
                    "name": name,
                    "lat": lat,
                    "lng": lon,
                    "note": metadata.get("Note", ""),
                    "category": category3 or category1 or "시설",
                    "desc": desc,
                    "distance": distances[i]
                })
        
        else:
            logger.warning("⚠️  ChromaDB 결과가 비어있음")
        
        logger.info(f"최종 반환: {len(facilities)}개 시설")
        facilities = facilities[:3]
        
        return json.dumps({
            "success": True,
            "facilities": facilities
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"❌ 검색 중 오류: {type(e).__name__}")
        logger.error(f"오류 메시지: {str(e)}")
        import traceback
        logger.error(f"스택 트레이스:\n{traceback.format_exc()}")
        
        return json.dumps({
            "success": False,
            "message": f"검색 중 오류: {str(e)}",
            "facilities": []
        }, ensure_ascii=False)