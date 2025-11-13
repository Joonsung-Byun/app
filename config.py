from pydantic_settings import BaseSettings
import torch

class Settings(BaseSettings):
    # API Keys
    OPENWEATHER_API_KEY: str = "72923a37d28c75e1c4c642947cfdab4b"
    KAKAO_API_KEY: str
    OPENAI_API_KEY: str
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "kid_program_collection_pca"
    
    # PCA Model
    PCA_MODEL_PATH: str = "./model_files/pca_model.joblib"
    
    # GPU & LLM
    USE_GPU: bool = torch.cuda.is_available()
    QWEN_MODEL_PATH: str = "./model_files/Qwen2-7B-Instruct"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    class Config:
        env_file = ".env"

settings = Settings()