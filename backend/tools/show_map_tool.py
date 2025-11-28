from langchain.tools import tool
from utils.conversation_memory import get_last_search_results, set_status, get_last_result_source
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
    (메모리에 저장된 최신 데이터를 조회하며, 좌표가 있는 경우만 지도를 생성합니다.)
    
    Args:
        conversation_id: 현재 대화 ID
        facility_indices: 표시할 시설 인덱스 (쉼표로 구분, 예: "0,1")
    """
    if not conversation_id:
        return json.dumps({"success": False, "message": "대화 ID 없음"}, ensure_ascii=False)

    set_status(conversation_id, "지도 데이터 구성 중..")
    
    # 1. 메모리에서 가장 최근 검색 결과 가져오기
    last_results = get_last_search_results(conversation_id)
    print(f"🗂️ 메모리에서 로드된 최근 검색 결과: {last_results}")

    last_tool_result = get_last_result_source(conversation_id)
    print(f"🗂️ 메모리에서 로드된 최근 검색 툴: {last_tool_result}")
    
    if not last_results:
        logger.warning(f"⚠️ 저장된 검색 결과가 없음: {conversation_id}")
        return json.dumps({
            "success": False, 
            "message": "지도에 표시할 최근 검색 결과가 없습니다.",
            "facilities": []
        }, ensure_ascii=False)

    logger.info(f"📍 메모리에서 로드된 시설 수: {len(last_results)}개")

    # 2. 인덱스 파싱
    try:
        indices = [int(idx.strip()) for idx in str(facility_indices).split(",") if idx.strip().isdigit()]
        if not indices: indices = [0, 1, 2] # 기본값
    except:
        indices = [0, 1, 2]

    filtered_facilities = []
    
    for idx in indices:
        if 0 <= idx < len(last_results):
            fac = last_results[idx]
            
            # 좌표 유효성 검사 (Safety Check)
            lat = fac.get('lat')
            lng = fac.get('lng')
            
            try:
                lat_float = float(lat) if lat is not None else 0.0
                lng_float = float(lng) if lng is not None else 0.0
            except (ValueError, TypeError):
                lat_float, lng_float = 0.0, 0.0

            # 좌표가 유효하지 않으면(0.0) 건너뜀 
            if lat_float == 0.0 and lng_float == 0.0:
                logger.warning(f"🚫 좌표 정보 없음(지도 생성 제외): {fac.get('name')}")
                continue

            filtered_facilities.append({
                "name": fac.get('name', '장소'),
                "lat": lat_float,
                "lng": lng_float,
                # "desc": fac.get('desc', '') or fac.get('description', '') or fac.get('addr', '')
            })
            
    # 3. 결과 반환
    # 유효한 좌표를 가진 시설이 하나도 없는 경우
    if not filtered_facilities:
        return json.dumps({
            "success": False, 
            "message": "선택한 장소들에 좌표 정보가 없습니다. (웹 검색 결과라면 'search_map_by_address' 도구를 사용하세요)",
            "facilities": []
        }, ensure_ascii=False)

    logger.info(f"✅ 지도 데이터 생성 완료: {len(filtered_facilities)}개")
    return json.dumps({
        "success": True,
        "facilities": filtered_facilities,
        "selected_indices": indices
    }, ensure_ascii=False)