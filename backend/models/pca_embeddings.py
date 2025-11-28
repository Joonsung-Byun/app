from langchain_openai import OpenAIEmbeddings
from config import settings
import logging

logger = logging.getLogger(__name__)

class OpenAIEmbeddingWrapper:
    """OpenAI text-embedding-3-large 모델을 사용하는 임베딩 래퍼"""
    
    def __init__(self):
        """OpenAI Embeddings 초기화"""
        try:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large",
                openai_api_key=settings.OPENAI_API_KEY,
                dimensions=3072  # text-embedding-3-large의 기본 차원
            )
            logger.info("✅ OpenAI Embeddings 초기화 성공 (text-embedding-3-large)")
        except Exception as e:
            logger.error(f"❌ OpenAI Embeddings 초기화 실패: {e}")
            raise
        
    async def aembed_query(self, text: str) -> list[float]:
        """
        쿼리 텍스트를 비동기로 임베딩 변환
        """
        try:
            # langchain_openai의 aembed_query 사용
            embedding = await self.embeddings.aembed_query(text)
            logger.info(f"✅ (Async) 쿼리 임베딩 생성 완료: {len(embedding)}차원")
            return embedding
        except Exception as e:
            logger.error(f"❌ (Async) 쿼리 임베딩 생성 실패: {e}")
            raise
    
    def embed_query(self, text: str) -> list[float]:
        """
        쿼리 텍스트를 임베딩으로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터 (3072차원)
        """
        try:
            embedding = self.embeddings.embed_query(text)
            logger.info(f"✅ 쿼리 임베딩 생성 완료: {len(embedding)}차원")
            return embedding
        except Exception as e:
            logger.error(f"❌ 쿼리 임베딩 생성 실패: {e}")
            raise
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        여러 문서를 임베딩으로 변환
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            embeddings = self.embeddings.embed_documents(texts)
            logger.info(f"✅ 문서 임베딩 생성 완료: {len(embeddings)}개, 각 {len(embeddings[0])}차원")
            return embeddings
        except Exception as e:
            logger.error(f"❌ 문서 임베딩 생성 실패: {e}")
            raise


# 전역 인스턴스 생성 (기존 pca_embeddings와 호환성 유지)
pca_embeddings = OpenAIEmbeddingWrapper()

logger.info("OpenAI Embeddings 래퍼 로드 완료")