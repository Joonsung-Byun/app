import requests
import json
from langchain.tools import tool
from config import settings

@tool
def search_map_by_address(place_name_or_address: str) -> str:
    """
    웹 검색 결과로 나온 장소명이나 주소를 받아, 지도에 표시할 수 있는 좌표와 링크를 생성합니다.
    RAG 검색 결과가 아닌, 텍스트로 된 장소의 위치를 찾을 때 사용하세요.
    """
    api_key = settings.KAKAO_API_KEY
    if not api_key:
        return "오류: 카카오 API 키가 설정되지 않았습니다."

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": place_name_or_address, "size": 1}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return f"카카오 지도 검색 실패 (상태코드: {response.status_code})"

        data = response.json()
        if not data.get('documents'):
            return f"'{place_name_or_address}'에 대한 위치 정보를 찾을 수 없습니다."

        # 가장 정확한 첫 번째 결과 사용
        place = data['documents'][0]
        name = place['place_name']
        address = place['road_address_name'] or place['address_name']
        lat = place['y']
        lng = place['x']
        place_url = place['place_url'] # 카카오맵 상세 링크

        # 지도 링크 생성 (좌표 기반)
        map_link = f"https://map.kakao.com/link/map/{name},{lat},{lng}"

        return json.dumps({
            "success": True,
            "name": name,
            "address": address,
            "lat": lat,
            "lng": lng,
            "kakao_map_link": map_link,
            "place_detail_url": place_url
        }, ensure_ascii=False)

    except Exception as e:
        return f"지도 검색 중 오류 발생: {str(e)}"