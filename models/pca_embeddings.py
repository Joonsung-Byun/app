from typing import List
import joblib
import numpy as np
from config import settings

class PCAEmbeddings:
    """PCA 기반 임베딩 (512차원)"""
    
    def __init__(self):
        print(f"PCA 모델 로딩 중: {settings.PCA_MODEL_PATH}")
        
        # PCA 모델 로드
        self.pca = joblib.load(settings.PCA_MODEL_PATH)
        print(f"✅ PCA 모델 로드 완료: {self.pca.n_components_}차원")
        
        # GPU 여부에 따라 분기
        if settings.USE_GPU:
            print("⚠️  GPU 모드: Mock 임베딩 사용 (개발용)")
            self.use_mock = True
        else:
            print("CPU 모드: OpenAI 임베딩 사용")
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.use_mock = False
        
        print("✅ 임베딩 준비 완료!")
    
    def _get_mock_embedding(self, text: str) -> np.ndarray:
        """Mock 임베딩 생성 (GPU 환경용)"""
        # 텍스트를 시드로 사용해서 일관성 유지
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        
        # PCA 입력 차원에 맞는 랜덤 벡터
        mock_embedding = np.random.randn(self.pca.n_features_in_)
        
        # 정규화 (실제 임베딩처럼 보이게)
        mock_embedding = mock_embedding / np.linalg.norm(mock_embedding)
        
        return mock_embedding
    
    def _get_openai_embedding(self, text: str) -> np.ndarray:
        """OpenAI 임베딩 생성 (CPU 환경용)"""
        response = self.client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        
        embeddings = np.array(response.data[0].embedding)
        
        # 차원 맞추기
        if len(embeddings) != self.pca.n_features_in_:
            if len(embeddings) > self.pca.n_features_in_:
                embeddings = embeddings[:self.pca.n_features_in_]
            else:
                embeddings = np.pad(
                    embeddings, 
                    (0, self.pca.n_features_in_ - len(embeddings))
                )
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """단일 쿼리 임베딩"""
        # GPU/CPU에 따라 다른 임베딩 사용
        if self.use_mock:
            embeddings = self._get_mock_embedding(text)
        else:
            embeddings = self._get_openai_embedding(text)
        
        # PCA 변환
        pca_embedding = self.pca.transform([embeddings])[0]
        
        return pca_embedding.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서 임베딩"""
        return [self.embed_query(text) for text in texts]

# 싱글톤 인스턴스
pca_embeddings = PCAEmbeddings()