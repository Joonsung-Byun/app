from pydantic_settings import BaseSettings
import torch

class Settings(BaseSettings):
    # Generation 모델
    GENERATION_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    EMBEDDING_MODEL: str = "Alibaba-NLP/gte-Qwen2-7B-instruct"
    # API Keys
    OPENWEATHER_API_KEY: str = "72923a37d28c75e1c4c642947cfdab4b"
    KAKAO_API_KEY: str = ""
    OPENAI_API_KEY: str
    NAVER_CLIENT_ID: str = ""      
    NAVER_CLIENT_SECRET: str = ""
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "kid_program_collection"
    
    # GPU & LLM
    USE_GPU: bool = torch.cuda.is_available()
    QWEN_MODEL_PATH: str = "./model_files/Qwen2-7B-Instruct"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    class Config:
        env_file = ".env"

settings = Settings()