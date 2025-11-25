from langchain.tools import tool
from utils.conversation_memory import get_last_search_results, set_status  #
from models.map_models import MapResponse, MapData, MapMarker, MapCenter
import json
import logging

logger = logging.getLogger(__name__)

@tool
def show_map_for_facilities(
    conversation_id: str,
    facility_indices: str = "0,1,2"
) -> str:
    """
    가장 최근 검색된 시설들의 지도 데이터를 생성합니다.
    (LLM을 쓰지 않고 메모리에 저장된 최신 데이터를 직접 조회합니다.)
    
    Args:
        conversation_id: 현재 대화 ID
        facility_indices: 표시할 시설 인덱스 (쉼표로 구분, 예: "0,1")
    """
    if not conversation_id:
        return json.dumps({"success": False, "message": "대화 ID 없음"}, ensure_ascii=False)

    set_status(conversation_id, "지도 데이터 구성 중..")
    
    # 1. 메모리에서 가장 최근 검색 결과 가져오기 (LLM 파싱 X)
    last_results = get_last_search_results(conversation_id)
    
    if not last_results:
        logger.warning(f"⚠️ 저장된 검색 결과가 없음: {conversation_id}")
        return json.dumps({
            "success": False, 
            "message": "지도에 표시할 최근 검색 결과가 없습니다.",
            "facilities": []
        }, ensure_ascii=False)

    logger.info(f"📍 메모리에서 로드된 시설 수: {len(last_results)}개")

    # 2. 인덱스 파싱 및 필터링
    try:
        # "0, 1" -> [0, 1]
        indices = [int(idx.strip()) for idx in str(facility_indices).split(",") if idx.strip().isdigit()]
        if not indices: indices = [0, 1, 2] # 기본값
    except:
        indices = [0, 1, 2]

    filtered_facilities = []
    
    for idx in indices:
        if 0 <= idx < len(last_results):
            # 메모리에 저장된 딕셔너리에서 정보 추출
            fac = last_results[idx]
            
            # 좌표가 없는 경우 방어 로직 (기본값: 서울시청)
            try:
                lat = float(fac.get('lat', 37.5665))
                lng = float(fac.get('lng', 126.9780))
            except:
                lat, lng = 37.5665, 126.9780
                
            filtered_facilities.append({
                "name": fac.get('name', '장소'),
                "lat": lat,
                "lng": lng,
                "desc": fac.get('desc', '') or fac.get('description', '') or fac.get('addr', '') # 다양한 키 대응
            })
            
    if not filtered_facilities:
        return json.dumps({
            "success": False, 
            "message": "선택한 인덱스에 해당하는 시설이 없습니다.",
            "facilities": []
        }, ensure_ascii=False)

    # 3. 결과 반환
    logger.info(f"✅ 지도 데이터 생성 완료: {len(filtered_facilities)}개")
    return json.dumps({
        "success": True,
        "facilities": filtered_facilities,
        "selected_indices": indices
    }, ensure_ascii=False)