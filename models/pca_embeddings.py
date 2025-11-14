from typing import List
import joblib
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel, BitsAndBytesConfig
from config import settings

class PCAEmbeddings:
    def __init__(self):
        print("="*70)
        print("🚀 PCA 임베딩 시스템 초기화")
        print("="*70)
        
        # PCA 모델 로드
        print(f"📥 PCA 모델 로딩: {settings.PCA_MODEL_PATH}")
        self.pca = joblib.load(settings.PCA_MODEL_PATH)
        print(f"✅ PCA 로드 완료! (입력: {self.pca.n_features_in_}, 출력: {self.pca.n_components_})")
        
        # 디바이스 확인
        self.device = "cuda" if (settings.USE_GPU and torch.cuda.is_available()) else "cpu"
        print(f"📱 Device: {self.device}")
        
        if self.device == "cpu":
            print("⚠️  경고: CPU 모드입니다. GPU 사용을 권장합니다!")
        
        # Alibaba GTE 모델 로드
        print(f"📥 임베딩 모델 로딩: {settings.EMBEDDING_MODEL}")
        print(f"⚠️  7B 모델 로딩 중... 시간이 걸립니다")
        
        self.tokenizer = AutoTokenizer.from_pretrained(settings.EMBEDDING_MODEL)
        
        # 4-bit quantization 설정 (GPU 8GB용)
        if self.device == "cuda":
            print("🔧 4-bit quantization 적용 (메모리 절약)")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            self.model = AutoModel.from_pretrained(
                settings.EMBEDDING_MODEL,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True
            )
        else:
            # CPU 모드
            self.model = AutoModel.from_pretrained(
                settings.EMBEDDING_MODEL,
                torch_dtype=torch.float32,
                trust_remote_code=True
            )
            self.model = self.model.to(self.device)
        
        self.model.eval()
        print(f"✅ 모델 로드 완료!")
        print("="*70)
    
    def _mean_pooling(self, model_output, attention_mask):
        """Mean Pooling"""
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def _get_gte_embedding(self, text: str) -> np.ndarray:
        """Alibaba GTE 임베딩 생성"""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = self._mean_pooling(outputs, inputs['attention_mask'])
        
        embedding = embeddings.cpu().numpy()[0]
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding
    
    def _adjust_dimension(self, embedding: np.ndarray) -> np.ndarray:
        """차원 조정"""
        target_dim = self.pca.n_features_in_
        current_dim = len(embedding)
        
        if current_dim == target_dim:
            return embedding
        elif current_dim > target_dim:
            return embedding[:target_dim]
        else:
            return np.pad(embedding, (0, target_dim - current_dim), mode='constant')
    
    def embed_query(self, text: str) -> List[float]:
        """단일 쿼리 임베딩"""
        embedding = self._get_gte_embedding(text)
        embedding = self._adjust_dimension(embedding)
        pca_embedding = self.pca.transform([embedding])[0]
        return pca_embedding.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서 임베딩"""
        embeddings = []
        for i, text in enumerate(texts):
            if (i + 1) % 100 == 0:
                print(f"   임베딩 진행: {i+1}/{len(texts)}")
            embedding = self._get_gte_embedding(text)
            embeddings.append(embedding)
        
        embeddings = np.array(embeddings)
        adjusted_embeddings = np.array([self._adjust_dimension(emb) for emb in embeddings])
        pca_embeddings = self.pca.transform(adjusted_embeddings)
        return pca_embeddings.tolist()

pca_embeddings = PCAEmbeddings()