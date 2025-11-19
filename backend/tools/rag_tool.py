from langchain.tools import tool
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from models.pca_embeddings import pca_embeddings
from typing import Optional
import json
import logging
from utils.conversation_memory import get_shown_facility_names

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
    collection = chroma_client.get_collection(
        name="kid_program_collection"
    )
    
except Exception as e:
    logger.error(f"❌ ChromaDB 연결 실패: {e}")
    collection = None

@tool
def search_facilities(
    original_query: str,
    conversation_id: str,
    k: int = 3  # 기본값을 3으로 설정 (유저가 개수 말 안 하면 3개)
) -> str:
    """
    사용자 질문과 가장 유사한 시설을 검색합니다.
    
    Args:
        original_query: 사용자의 원본 질문 (예: "부산 자전거 타기 좋은 곳")
        conversation_id: 현재 대화 ID
        k: 반환할 결과 개수. 사용자가 구체적인 개수(예: '2군데', '하나만')를 언급하면 그 숫자를 입력하세요. 언급이 없으면 기본값 3을 사용합니다.
    
    Returns:
        시설 정보 JSON (유사도 높은 순으로 정렬)
    """
    logger.info(f"\n{'='*50}")
    logger.info(f"시설 검색 시작")
    logger.info(f"original_query: {original_query}, k: {k}")
    logger.info(f"{'='*50}")

    if not conversation_id:
        logger.error("conversation_id가 전달되지 않았습니다.")
        return json.dumps({
            "success": False,
            "message": "대화 ID가 없어 검색을 진행할 수 없습니다.",
            "facilities": []
        }, ensure_ascii=False)
    
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
        query_embedding = pca_embeddings.embed_query(query_text)
        
        # 벡터 검색
        print("ChromaDB 벡터 검색 중...")
        
        facilities_names_already_shown = get_shown_facility_names(conversation_id) if conversation_id else []
        print(f"지금까지 보여준 시설들: {facilities_names_already_shown}")

        if facilities_names_already_shown == []:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=["metadatas", "documents", "distances"]
            )
        else:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                where={
                    "Name": {"$nin": facilities_names_already_shown}
                },
                include=["metadatas", "documents", "distances"]
            )
        
        logger.info(f"✅ 벡터 검색 완료: {len(results['ids'][0])}개")
        
        facilities = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            distances = results['distances'][0]

            # 지역, 연령대
            
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
        facilities = facilities[:k]  # 상위 k개
        
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
