from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
import torch
from config import settings

def get_llm():
    """GPU 여부에 따라 LLM 반환"""
    if settings.USE_GPU and torch.cuda.is_available():
        print("="*70)
        print("🚀 Qwen 2.5 7B 모델 로딩 중...")
        print("="*70)
        
        tokenizer = AutoTokenizer.from_pretrained(
            settings.GENERATION_MODEL,
            trust_remote_code=True
        )
        
        # 4-bit quantization (8GB GPU용)
        print("🔧 4-bit quantization 적용")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            settings.GENERATION_MODEL,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        print("✅ 모델 로드 완료!")
        
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            top_p=0.9
        )
        
        print("✅ 파이프라인 준비 완료!")
        print("="*70)
        
        return HuggingFacePipeline(pipeline=pipe)
    
    else:
        print("⚠️  CPU 모드: OpenAI API 사용")
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=settings.OPENAI_API_KEY
        )