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

# 유사도 커트라인
# 테스트해보면서 1.0 ~ 1.5 사이로 조절 필요. 숫자가 작을수록 엄격함.
SIMILARITY_THRESHOLD = 1.3 

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
    
    logger.info(f"✅ ChromaDB 연결 성공: {collection.name}")
    logger.info(f"컬렉션 항목 수: {collection.count()}")
    
except Exception as e:
    logger.error(f"❌ ChromaDB 연결 실패: {e}")
    collection = None

@tool
def search_facilities(
    original_query: str,
    conversation_id: str,
    location: str = "",  # 🟢 [추가] 지역 필터링을 위한 파라미터
    k: int = 3 
) -> str:
    """
    사용자 질문과 가장 유사한 시설을 검색합니다.
    
    Args:
        original_query: 사용자의 원본 질문 (예: "부산 자전거 타기 좋은 곳")
        conversation_id: 현재 대화 ID (중복 추천 방지용)
        location: 사용자가 언급한 지역명 (예: "부산", "송파"). 없으면 빈 문자열.
        k: 반환할 결과 개수.
    """
    logger.info(f"\n{'='*50}")
    logger.info(f"시설 검색 시작 | Query: {original_query} | Loc: {location}")
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
    
    try:
        # 임베딩 생성
        query_embedding = pca_embeddings.embed_query(original_query)
        
        # 중복 방지 (이미 보여준 시설 이름 가져오기)
        facilities_names_already_shown = get_shown_facility_names(conversation_id) if conversation_id else []
        logger.info(f"제외할 시설들(중복): {facilities_names_already_shown}")

        # 쿼리 실행 (중복 제외 로직 포함)
        if facilities_names_already_shown == []:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=10, # 넉넉하게 가져와서 필터링함
                include=["metadatas", "documents", "distances"]
            )
        else:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=10, # 넉넉하게 가져와서 필터링함
                where={
                    "Name": {"$nin": facilities_names_already_shown}
                },
                include=["metadatas", "documents", "distances"]
            )
        
        logger.info(f"✅ 벡터 검색 완료: {len(results['ids'][0])}개 후보")
        
        facilities = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            distances = results['distances'][0]
            
            for i, metadata in enumerate(metadatas):
                name = metadata.get("Name", metadata.get("name", "이름없음"))
                current_dist = distances[i]
                
                # 🟡 [위치 이동] 주소를 필터링에 써야 해서 미리 가져옴
                address = metadata.get("Address", "")

                # 1. 유사도 점수 필터링
                if current_dist > SIMILARITY_THRESHOLD:
                    logger.warning(f"  ❌ [점수미달] {name} ({current_dist:.4f})")
                    continue 
                
                # 2. 🟢 [추가] 지역명 강제 필터링 (핵심!)
                # 사용자가 '부산'이라고 했는데 주소에 '부산'이 없으면 탈락시킴
                if location and location not in address:
                    logger.warning(f"  ❌ [지역불일치] {name} (요청: {location} != 주소: {address})")
                    continue

                logger.info(f"  ✅ [통과] {name} ({current_dist:.4f})")
                
                # 좌표 변환
                lat = metadata.get("LAT", "37.5665")
                lon = metadata.get("LON", "126.9780")
                try:
                    lat = float(lat)
                    lon = float(lon)
                except (ValueError, TypeError):
                    lat = 37.5665
                    lon = 126.9780
                
                # 설명 생성
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
                    "distance": current_dist
                })
        
        else:
            logger.warning("⚠️  ChromaDB 결과가 비어있음")
        
        logger.info(f"최종 유효 결과: {len(facilities)}개")
        
        # 요청한 개수(k)만큼 자르기
        facilities = facilities[:k]
        
        return json.dumps({
            "success": True,
            "count": len(facilities),
            "facilities": facilities
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"❌ 검색 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return json.dumps({
            "success": False,
            "message": f"검색 중 오류: {str(e)}",
            "facilities": []
        }, ensure_ascii=False)