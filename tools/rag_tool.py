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
    
    collection = chroma_client.get_collection(
        name=settings.CHROMA_COLLECTION
    )
    
    logger.info(f"✅ ChromaDB 연결 성공: {settings.CHROMA_COLLECTION}")
    logger.info(f"컬렉션 항목 수: {collection.count()}")
    
except Exception as e:
    logger.error(f"❌ ChromaDB 연결 실패: {e}")
    collection = None

@tool
def search_facilities(
    region: str,
    is_indoor: bool,
    original_query: Optional[str] = None,  # ← 추가
    child_age: Optional[int] = None,
    k: int = 3
) -> str:
    """
    조건에 맞는 시설을 검색합니다.
    
    Args:
        region: 지역명 (예: "부산", "서울", "창원")
        is_indoor: 실내 여부 (True=실내, False=실외)
        original_query: 사용자의 원본 질문 (예: "자전거 타기 좋은 곳")
        child_age: 아이 나이 (선택, None이면 무시)
        k: 결과 개수
    
    Returns:
        시설 정보 JSON
    """
    logger.info(f"\n{'='*50}")
    logger.info(f"시설 검색 시작")
    logger.info(f"region: {region}, is_indoor: {is_indoor}")
    print(f"original_query: {original_query}, child_age: {child_age}, k: {k}")
    logger.info(f"{'='*50}")
    
    if collection is None:
        logger.error("ChromaDB 컬렉션이 없음")
        return json.dumps({
            "success": False,
            "message": "ChromaDB 연결 실패",
            "facilities": []
        }, ensure_ascii=False)
    
    target_condition = "실내" if is_indoor else "실외"
    
    # 쿼리 텍스트 생성 (원본 쿼리 있으면 포함!)
    if original_query:
        query_text = f"{region} {target_condition} {original_query}"
    else:
        query_text = f"{region} {target_condition} 아이 시설"
    
    print(f"쿼리 텍스트: {query_text}")
    
    try:
        # 임베딩 생성
        print("임베딩 생성 중...")
        query_embedding = pca_embeddings.embed_query(query_text)
        print(f"✅ 임베딩 완료: {len(query_embedding)}차원")
        
        # 벡터 검색
        print("ChromaDB 벡터 검색 중...")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["metadatas", "documents", "distances"]
        )

        print(f"results: {results}")
        
        logger.info(f"✅ 벡터 검색 완료: {len(results['ids'][0])}개")
        
        facilities = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            distances = results['distances'][0]
            
            # 필터링된 항목 수집
            filtered_items = []
            
            for i, metadata in enumerate(metadatas):
                signgu = metadata.get("SIGNGU_NM", "")
                ctprvn = metadata.get("CTPRVN_NM", "")
                name = metadata.get("Name", metadata.get("name", "이름없음"))
                in_out = metadata.get("in_out", "")
                
                # 1. 지역 필터링
                region_match = region in signgu or region in ctprvn
                
                if not region_match:
                    continue
                
                # 2. 실내/실외 필터링
                if in_out != target_condition:
                    continue
                
                # 3. 연령 필터링 (child_age가 None이면 무시)
                if child_age is not None:
                    age_min = metadata.get("age_min", "")
                    age_max = metadata.get("age_max", "")
                    
                    if age_min and age_max:
                        try:
                            age_min = int(age_min)
                            age_max = int(age_max)
                            
                            if not (age_min <= child_age <= age_max):
                                continue
                        except (ValueError, TypeError):
                            pass
                
                # 필터링 통과
                filtered_items.append({
                    "metadata": metadata,
                    "document": documents[i] if i < len(documents) else "",
                    "name": name,
                    "in_out": in_out,
                    "distance": distances[i]
                })

                logger.info(f"filttered_itemS: {filtered_items}")
            
            logger.info(f"필터링 후 남은 항목: {len(filtered_items)}개")
            
            if len(filtered_items) == 0:
                logger.warning(f"⚠️  {region} {target_condition} 시설을 찾을 수 없음")
                return json.dumps({
                    "success": True,
                    "facilities": []
                }, ensure_ascii=False)
            
            # 거리순 정렬 (유사도 높은 순)
            filtered_items.sort(key=lambda x: x["distance"])
            
            # 상위 k개 선택
            for idx, item in enumerate(filtered_items[:k]):
                metadata = item["metadata"]
                name = item["name"]
                
                logger.info(f"  ✅ [{idx+1}] {name} (distance: {item['distance']:.4f})")
                
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
                if item["document"]:
                    desc = item["document"][:100]
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
                    "desc": desc
                })
        
        else:
            logger.warning("⚠️  ChromaDB 결과가 비어있음")
        
        logger.info(f"최종 반환: {len(facilities)}개 시설")
        
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