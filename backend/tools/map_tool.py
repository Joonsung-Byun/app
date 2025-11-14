from langchain.tools import tool
from typing import List, Dict

@tool
def generate_kakao_map_link(facilities: List[Dict]) -> str:
    """
    카카오맵 링크 생성
    
    Args:
        facilities: 시설 정보 리스트
    
    Returns:
        카카오맵 링크
    """
    if not facilities:
        return ""
    
    center = facilities[0]
    lat, lng = center["lat"], center["lng"]
    
    link = f"https://map.kakao.com/link/map/{center['name']},{lat},{lng}"
    
    return link