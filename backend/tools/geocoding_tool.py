import requests
import logging
from config import settings
from models.map_models import MapResponse, MapData, MapCenter, MapMarker

logger = logging.getLogger(__name__)

def search_map_by_address_core(place_name_or_address: str) -> MapResponse:
    """
    Kakao API를 호출해 MapResponse 객체를 직접 반환하는 '핵심 로직 함수'
    검색 실패 시, 단어를 뒤에서부터 하나씩 제거하며 재시도합니다. (예: '벡스코 4홀' -> '벡스코')
    """

    api_key = settings.KAKAO_REST_API_KEY
    
    # 기본 실패 응답 (API 키 없음 등)
    default_fail_response = MapResponse(
        link="",
        data=MapData(center=MapCenter(lat=0, lng=0), markers=[]),
        type="text",
        content="지도를 생성할 수 있는 장소를 찾지 못했어요. 😢"
    )

    if not api_key:
        logger.error("KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        return default_fail_response

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}

    # 🟢 [핵심 수정] 재귀적 검색 로직 (Smart Retry)
    current_query = place_name_or_address.strip()
    found_document = None
    
    # 최대 3번까지만 단어를 줄여봄 (무한 루프 방지)
    max_retries = 3
    retry_count = 0

    while current_query and retry_count <= max_retries:
        try:
            params = {"query": current_query, "size": 1}
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get("documents", [])
                
                if documents:
                    # 찾았다!
                    found_document = documents[0]
                    logger.info(f"✅ 검색 성공: '{current_query}' (원본: {place_name_or_address})")
                    break 
            
        except Exception as e:
            logger.warning(f"검색 중 오류 발생: {e}")
            break

        # 못 찾았으면 뒤에서 한 단어 제거하고 재시도
        # 예: "부산 벡스코 4홀" (실패) -> "부산 벡스코" (재시도)
        words = current_query.split()
        if len(words) > 1:
            removed_word = words[-1]
            current_query = " ".join(words[:-1])
            retry_count += 1
            logger.info(f"검색 실패 ('{removed_word}' 제거), 재시도: '{current_query}'")
        else:
            break # 단어가 1개뿐이면 더 이상 줄일 수 없음

    # --- 결과 처리 ---

    # 1. 끝내 못 찾은 경우
    if not found_document:
        # 검색 결과 페이지라도 제공 (Fallback)
        fallback_link = f"https://map.kakao.com/link/search/{place_name_or_address}"
        return MapResponse(
            link=fallback_link,
            data=MapData(center=MapCenter(lat=0, lng=0), markers=[]),
            type="text",
            content=f"죄송해요, '{place_name_or_address}'의 정확한 지도 핀을 찍지 못했어요. 😢\n대신 검색 결과 링크를 드릴게요!",
        )

    # 2. 찾은 경우
    place = found_document
    name = place.get("place_name") or place_name_or_address
    address = place.get("road_address_name") or place.get("address_name") or "주소 정보 없음"

    try:
        lat = float(place["y"])
        lng = float(place["x"])
    except Exception as e:
        logger.warning(f"좌표 변환 실패, 기본값 사용: {e}")
        lat, lng = 37.5665, 126.9780

    kakao_link = f"https://map.kakao.com/link/to/{name},{lat},{lng}"

    return MapResponse(
        link=kakao_link,
        data=MapData(
            center=MapCenter(lat=lat, lng=lng),
            markers=[
                MapMarker(
                    name=name,
                    lat=lat,
                    lng=lng,
                    desc=address
                )
            ]
        )
    )