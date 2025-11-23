from fastapi import APIRouter
import requests
from config import settings

router = APIRouter()

@router.get("/programs")
def get_programs(facility_id: int):
    url = f"{settings.SUPABASE_URL}/rest/v1/programs"

    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    }

    # Supabase query → facility_id 필터링
    params = {
        "select": "*",
        "facility_id": f"eq.{facility_id}"
    }

    res = requests.get(url, headers=headers, params=params)

    print("프로그램 응답:", res.status_code, res.text)

    return res.json()
