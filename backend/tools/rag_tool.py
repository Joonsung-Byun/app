from langchain.tools import tool
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from models.pca_embeddings import pca_embeddings
from typing import Optional
import json
import logging
from utils.conversation_memory import get_shown_facility_names, set_status
from utils.location_mapper import CITY_TO_PROVINCE_SIGNGU
from .naver_search_tool import naver_web_search

logger = logging.getLogger(__name__)

def _safe_float(value, default=0.0) -> float:
    """숫자 변환이 실패하면 기본값 반환"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# 임계값 (엄격하게 적용)
SIMILARITY_THRESHOLD = 1.1 

# 주소 필터링 시 무시할 일반 단어들
IGNORE_LOCATION_TERMS = ["입구", "출구", "기구", "친구", "야구", "축구", "농구", "배구", "도구", "문구", "아동", "운동", "활동", "행동"]

# ChromaDB 클라이언트 초기화
try:
    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    collection = chroma_client.get_collection(name="kid_program_collection")
except Exception as e:
    logger.error(f"❌ ChromaDB 연결 실패: {e}")
    collection = None

@tool
async def search_facilities(
    original_query: str,
    conversation_id: str,
    location: str = "",
    indoor_outdoor: str = "",
    k: int = 3 
) -> str:
    """
    사용자 질문과 가장 유사한 시설을 RAG(DB)에서 검색합니다.
    지역명(시/군/구/동)과 실내외 여부를 정밀하게 필터링합니다.
    """
    logger.info(f"🔍 RAG 검색 | Q: {original_query} | Loc: {location} | InOut: {indoor_outdoor}")
    
    if conversation_id:
        set_status(conversation_id, "시설 후보 찾는 중..")

    if collection is None:
        return json.dumps({"success": False, "facilities": []})
    
    try:
        # 임베딩 생성 (비동기 전환)
        query_embedding = await pca_embeddings.aembed_query(original_query)
        shown_facilities = get_shown_facility_names(conversation_id) if conversation_id else []

        # -------------------------------------------------------------------
        # Pre-filtering: location 매핑 정보를 활용해 Chroma where 절 적용
        # -------------------------------------------------------------------
        where_clause = None
        if location:
            loc_info = CITY_TO_PROVINCE_SIGNGU.get(location)
            if loc_info:
                ctprvn_nm = loc_info[0]
                if len(loc_info) > 1:
                    signgu_nm = loc_info[1]
                    where_clause = {
                        "$and": [
                            {"CTPRN_NM": {"$eq": ctprvn_nm}},
                            {"SIGNGU_NM": {"$eq": signgu_nm}}
                        ]
                    }
                    logger.info(f"⚡ 지역 정밀 필터(시도+시군구): {ctprvn_nm} {signgu_nm}")
                else:
                    where_clause = {"CTPRN_NM": {"$eq": ctprvn_nm}}
                    logger.info(f"⚡ 지역 광역 필터(시도): {ctprvn_nm}")
            else:
                logger.warning(f"⚠️ 매핑되지 않은 지역명: {location} (사전 필터 미적용)")

        # 쿼리 실행 (사전 필터 where_clause 적용)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=50,
            where=where_clause,
            include=["metadatas", "documents", "distances"]
        )

        # 지역 where 필터로 0건이면 필터 제거 후 재시도
        if (
            (not results)
            or (not results.get("ids"))
            or (not results["ids"][0])
        ) and where_clause:
            logger.warning("⚠️ 지역 where 필터 결과 0건 -> 필터 없이 재시도")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=50,
                include=["metadatas", "documents", "distances"]
            )
        
        facilities = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            distances = results['distances'][0]
            
            # 상세 주소 필터링용 단어 추출
            query_words = original_query.split()
            detail_locations = []
            for w in query_words:
                if len(w) >= 2 and w[-1] in ["시", "군", "구", "동", "읍", "면"]:
                    if w not in IGNORE_LOCATION_TERMS:
                        detail_locations.append(w)
            
            if detail_locations:
                logger.info(f"📍 상세 지역 필터 감지: {detail_locations}")

            for i, metadata in enumerate(metadatas):
                name = metadata.get("Name", metadata.get("name", "이름없음"))
                address = metadata.get("Address", "")
                db_in_out = metadata.get("in_out", "") 
                current_dist = distances[i]

                # [필터링 1] 중복 제외
                if name in shown_facilities:
                    continue

                # [필터링 2] 유사도 거리
                if current_dist > SIMILARITY_THRESHOLD:
                    logger.warning(f"  ❌ [탈락:거리] {name} ({current_dist:.2f})")
                    continue 

                # [필터링 3] 기본 지역 필터
                if location and location not in address:
                    logger.warning(f"  ❌ [탈락:지역기본] {name} (주소:{address} vs 요청:{location})")
                    continue

                # [필터링 4] 상세 주소 필터
                is_detail_match = True
                for detail_loc in detail_locations:
                    if detail_loc not in address:
                        logger.warning(f"  ❌ [탈락:세부지역] {name} (주소에 '{detail_loc}' 없음)")
                        is_detail_match = False
                        break
                if not is_detail_match:
                    continue

                # [필터링 5] 실내/실외
                if indoor_outdoor:
                    if indoor_outdoor not in db_in_out:
                         logger.warning(f"  ❌ [탈락:실내외] {name} (DB:{db_in_out} != Req:{indoor_outdoor})")
                         continue

                # 통과
                category = metadata.get("Category3") or metadata.get("Category1")
                desc = documents[i][:100] if i < len(documents) else address[:100]
                lat_val = _safe_float(metadata.get("LAT", 0.0))
                lng_val = _safe_float(metadata.get("LON", 0.0))

                facilities.append({
                    "name": name,
                    "lat": lat_val,
                    "lng": lng_val,
                    "category": category,
                    "desc": desc,
                    "in_out": db_in_out
                })

        facilities = facilities[:k]
        
        # [Fallback] RAG 검색 결과 0건 시, naver_web_search 폴백 실행
        if not facilities:
            logger.warning("🚫 RAG 검색 결과 0건. naver_web_search로 폴백 실행.")
            set_status(conversation_id, "RAG 결과 부족으로 웹 검색 폴백 실행 중...")
            
            fallback_query = original_query if not location else f"{original_query} {location}"
            web_search_output = await naver_web_search.ainvoke({
                "query": fallback_query,
                "conversation_id": conversation_id
            })
            return web_search_output 

        logger.info(f"✅ 최종 RAG 결과: {len(facilities)}개 반환")
        
        return json.dumps({
            "success": True,
            "count": len(facilities),
            "facilities": facilities
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"❌ RAG 검색 오류: {e}")
        return json.dumps({"success": False, "facilities": []})
