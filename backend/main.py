from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat_router  # 수정
import requests
from config import settings

app = FastAPI(title="Kids Guide Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["chat"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get('/facilities')
def get_facilities(
    category2: str = None,
    minLat: float = None,
    maxLat: float = None,
    minLon: float = None,
    maxLon: float = None
):
    url = f"{settings.SUPABASE_URL}/rest/v1/aigo-location"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    }

    params = {"select": "*"}

    print("요청 파라미터:", category2, minLat, maxLat, minLon, maxLon)

    # ✔ 카테고리 필터
    if category2:
        params["Category2"] = f"eq.{category2}"

    # ✔ 지도 Bounds 필터
    if minLat is not None:
        params["LAT"] = f"gte.{minLat}"

    if maxLat is not None:
        params["LAT"] = f"lte.{maxLat}"

    if minLon is not None:
        params["LON"] = f"gte.{minLon}"

    if maxLon is not None:
        params["LON"] = f"lte.{maxLon}"

    res = requests.get(url, headers=headers, params=params)
    print("응답:", res.status_code)
    # print(res.text)

    return res.json()
