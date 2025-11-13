from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from config import settings  # app/ 가 루트이므로

def get_llm():
    """GPU 여부에 따라 LLM 반환"""
    if settings.USE_GPU:
        # QWEN 로컬 모델
        tokenizer = AutoTokenizer.from_pretrained(settings.QWEN_MODEL_PATH)
        model = AutoModelForCausalLM.from_pretrained(
            settings.QWEN_MODEL_PATH,
            device_map="auto",
            torch_dtype="auto"
        )
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            temperature=0.7,
        )
        return HuggingFacePipeline(pipeline=pipe)
    else:
        # OpenAI API
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY
        )