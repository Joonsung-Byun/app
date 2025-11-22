from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat_router  # 수정
import requests
from config import settings
from routers.facilities_router import router as facilities_router

app = FastAPI(title="Kids Guide Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(facilities_router, tags=["facilities"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

