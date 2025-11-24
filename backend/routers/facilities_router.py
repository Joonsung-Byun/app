from fastapi import APIRouter
import requests
from config import settings

router = APIRouter()

@router.get("/facilities")
def get_facilities(
    category2: str = None,
    minLat: float = None,
    maxLat: float = None,
    minLon: float = None,
    maxLon: float = None
):
    url = f"{settings.SUPABASE_URL}/rest/v1/facilities"

    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    }

    params = [("select", "*")]


    # category filter
    if category2:
        params.append(("category2", f"eq.{category2}"))

    # Bounds filters (중복 key 허용 → 리스트 append 방식)
    if minLat is not None:
        params.append(("lat", f"gte.{minLat}"))
    if maxLat is not None:
        params.append(("lat", f"lte.{maxLat}"))
    if minLon is not None:
        params.append(("lon", f"gte.{minLon}"))
    if maxLon is not None:
        params.append(("lon", f"lte.{maxLon}"))

    res = requests.get(url, headers=headers, params=params)

    print("응답:", res.status_code, res.text)

    return res.json()
