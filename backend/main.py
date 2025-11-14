from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat_router  # 수정

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