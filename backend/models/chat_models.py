from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
import torch
import requests
import logging
from config import settings

logger = logging.getLogger(__name__)

def get_llm():
    if settings.LLM_BACKEND == "auto":
        try:
            response = requests.get(f"{settings.VLLM_ENDPOINT}/models", timeout=2)
            if response.status_code == 200:
                print(f"✅ vLLM 서버 감지됨: {settings.VLLM_ENDPOINT}")
                return ChatOpenAI(
                    model=settings.VLLM_MODEL_NAME,
                    openai_api_key="EMPTY",
                    base_url=settings.VLLM_ENDPOINT,
                    temperature=0.7,
                )
        except Exception as e:
            print(f"⚠️ vLLM 서버 연결 실패, OpenAI로 폴백: {e}")
    
    # OpenAI 사용 (auto 실패 시 또는 openai 모드)
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=settings.OPENAI_API_KEY
    )