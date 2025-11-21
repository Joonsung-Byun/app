from pydantic import BaseModel
from typing import List


class MapMarker(BaseModel):
    """
    지도에 표시할 개별 마커(시설) 정보
    """
    name: str
    lat: float
    lng: float
    desc: str


class MapCenter(BaseModel):
    """
    지도 중심 좌표
    """
    lat: float
    lng: float


class MapData(BaseModel):
    """
    프론트에서 사용할 지도 데이터 (center + markers)
    mockResponse.ts의 data 구조와 동일한 역할
    """
    center: MapCenter
    markers: List[MapMarker]


class MapResponse(BaseModel):
    """
    프론트에 내려보낼 최종 지도 메시지 형태
    mockResponse.ts에서 map 응답에 해당
    """
    role: str = "ai"
    type: str = "map"
    content: str = ""
    link: str
    data: MapData