import uvicorn
from config import settings  # 수정

if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # 수정
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )