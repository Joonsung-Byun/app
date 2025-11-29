from langchain.tools import tool
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from models.pca_embeddings import pca_embeddings
from typing import Optional
import json
import logging
from utils.conversation_memory import get_shown_facility_names, set_status
from utils.location_mapper import CITY_TO_PROVINCE_SIGNGU, extract_location

logger = logging.getLogger(__name__)

# 임계값
SIMILARITY_THRESHOLD = 1.35 

# 주소 필터링 시 무시할 일반 단어들
IGNORE_LOCATION_TERMS = ["입구", "출구", "기구", "친구", "야구", "축구", "농구", "배구", "도구", "문구", "아동", "운동", "활동", "행동"]

# ChromaDB 클라이언트 초기화
try:
    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    collection = chroma_client.get_collection(name=settings.CHROMA_COLLECTION)
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
    지역명(시/군/구/동)과 실내외 여부("실내" 또는 "실외")를 정밀하게 필터링합니다.
    """
    print(f"🔍 RAG 검색 | Q: {original_query} | Loc: {location} | InOut: {indoor_outdoor} | 유저가 부탁한 수: {k},"  )
    
    if conversation_id:
        set_status(conversation_id, "시설 후보 찾는 중..")

    if collection is None:
        return json.dumps({"success": False, "facilities": []})
    
    try:
        # 임베딩 생성 (비동기 전환)
        query_embedding = await pca_embeddings.aembed_query(original_query)
        shown_facilities = get_shown_facility_names(conversation_id) if conversation_id else []

        # [Normalization] indoor_outdoor 값 정규화 (indoor -> 실내, outdoor -> 실외)
        if indoor_outdoor:
            if indoor_outdoor.lower() in ["indoor", "inside"]:
                indoor_outdoor = "실내"
            elif indoor_outdoor.lower() in ["outdoor", "outside"]:
                indoor_outdoor = "실외"
            logger.info(f"🔄 실내외 필터 정규화: {indoor_outdoor}")

        # ---------------------------------------------------------
        # WHERE 절 구성
        #   1) 이미 노출된 시설 제외 (shown_facilities)
        #   2) location(도시) -> CTPRVN_NM / SIGNGU_NM
        #   3) 실내/실외(in_out) 필터
        # ---------------------------------------------------------
        where_filters = []

        # 1) 이미 보여준 시설 제외 (DB 레벨)
        exclude_names_filter = None
        if shown_facilities:
            exclude_names_filter = {"Name": {"$nin": shown_facilities}}
            where_filters.append(exclude_names_filter)
            print(f"[RAG] shown_facilities 제외 필터: {shown_facilities}")

        # 2) 실내/실외(in_out) 필터 (DB 레벨)
        inout_filter = None
        if indoor_outdoor:
            inout_filter = {"in_out": {"$eq": indoor_outdoor}}
            where_filters.append(inout_filter)
            print(f"[RAG] 실내/실외 필터: {indoor_outdoor}")

        # 3) 지역 필터 (CITY_TO_PROVINCE_SIGNGU 사용 -> CTPRVN_NM / SIGNGU_NM)
        location_filter = None
        if location:
            loc_info = CITY_TO_PROVINCE_SIGNGU.get(location)
            if loc_info:
                ctprvn_nm = loc_info[0]  # 시도명
                if len(loc_info) > 1:
                    signgu_nm = loc_info[1]  # 시/군/구명
                    location_filter = {
                        "$and": [
                            {"CTPRVN_NM": {"$eq": ctprvn_nm}},
                            {"SIGNGU_NM": {"$eq": signgu_nm}}
                        ]
                    }
                    logger.info(f"⚡ 지역 정밀 필터(시도+시군구): {ctprvn_nm} {signgu_nm}")
                    print(f"[RAG] 지역 정밀 필터: {ctprvn_nm} {signgu_nm}")
                else:
                    location_filter = {"CTPRVN_NM": {"$eq": ctprvn_nm}}
                    logger.info(f"⚡ 지역 광역 필터(시도): {ctprvn_nm}")
                    print(f"[RAG] 지역 광역 필터: {ctprvn_nm}")
                where_filters.append(location_filter)
            else:
                logger.warning(f"⚠️ 매핑되지 않은 지역명: {location} (사전 필터 미적용)")
                print(f"[RAG] 매핑되지 않은 지역명: {location}")

        # where_filters 리스트를 최종 where_clause로 조립
        if not where_filters:
            where_clause = None
        elif len(where_filters) == 1:
            where_clause = where_filters[0]
        else:
            where_clause = {"$and": where_filters}

        print(f"[RAG] 최종 where_clause: {json.dumps(where_clause, ensure_ascii=False) if where_clause else 'None'}")

        # 쿼리 실행 (사전 필터 where_clause 적용)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=20,
            where=where_clause,
            include=["metadatas", "documents", "distances"]
        )

        # 지역 where 필터로 0건이면 location 조건만 제거 후 재시도
        if (
            (not results)
            or (not results.get("ids"))
            or (not results["ids"][0])
        ) and where_clause:
            logger.warning("⚠️ 지역 where 필터 결과 0건 -> location 조건 제거 후 재시도")

            # location 조건을 제외하고 shown_facilities/in_out 필터만 유지
            fallback_filters = []
            if exclude_names_filter:
                fallback_filters.append(exclude_names_filter)
            if inout_filter:
                fallback_filters.append(inout_filter)

            if not fallback_filters:
                fallback_where = None
            elif len(fallback_filters) == 1:
                fallback_where = fallback_filters[0]
            else:
                fallback_where = {"$and": fallback_filters}

            print(f"[RAG] fallback where_clause (location 제거): {json.dumps(fallback_where, ensure_ascii=False) if fallback_where else 'None'}")

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=20,
                where=fallback_where,
                include=["metadatas", "documents", "distances"]
            )
        
        facilities = []
        
        if results and results['ids'] and len(results['ids'][0]) > 0:
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            distances = results['distances'][0]

            for i, metadata in enumerate(metadatas):
                name = metadata.get("Name", metadata.get("name", "이름없음"))
                address = metadata.get("Address", "")
                db_in_out = metadata.get("in_out", "") 
                current_dist = distances[i]

                # [필터링 2] 유사도 거리
                if current_dist > SIMILARITY_THRESHOLD:
                    logger.warning(f"  ❌ [탈락:거리] {name} ({current_dist:.2f})")
                    continue 

                # 통과
                category = metadata.get("Category3") or metadata.get("Category1")
                desc = documents[i][:100] if i < len(documents) else address[:100]
                lat_val = metadata.get("LAT", 0.0)
                lng_val = metadata.get("LON", 0.0)

                facilities.append({
                    "name": name,
                    "lat": lat_val,
                    "lng": lng_val,
                    "category": category,
                    "desc": desc,
                    "in_out": db_in_out
                })

        facilities = facilities[:k]

        # RAG 검색 결과 정리
        if not facilities:
            logger.warning("🚫 RAG 검색 결과 0건.")
            return json.dumps({
                "success": True,
                "count": 0,
                "facilities": []
            }, ensure_ascii=False)

        logger.info(f"✅ 최종 RAG 결과: {len(facilities)}개 반환")
        
        return json.dumps({
            "success": True,
            "count": len(facilities),
            "facilities": facilities
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"❌ RAG 검색 오류: {e}")
        return json.dumps({"success": False, "facilities": []})
