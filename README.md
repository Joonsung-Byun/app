# Kids Chatbot - 가족 나들이 추천 챗봇

Monorepo 구조로 Backend(FastAPI)와 Frontend(React)를 관리합니다.

## 📁 프로젝트 구조

```
kids-chatbot/
├── backend/     # FastAPI + LangChain + ChromaDB + OpenAI
└── frontend/    # React + TypeScript + Kakao Map API
```

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI
- **LLM**: Claude 3.5 Sonnet (Anthropic)
- **Embeddings**: OpenAI text-embedding-3-large
- **Vector DB**: ChromaDB
- **Agent Framework**: LangChain

### Frontend
- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **Map**: Kakao Map API

## 🚀 실행 방법

### Backend

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 의존성 설치
pip install -r requirements.txt

# ChromaDB 실행 (Docker)
docker-compose up -d

# 서버 실행
python main.py
# 또는
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

## 📝 환경 변수 설정

### Backend (.env)
```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
WEATHER_API_KEY=your_weather_api_key

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=kid_program_collection_pca
```

### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8000
VITE_KAKAO_MAP_API_KEY=your_kakao_map_api_key
```

## 🧪 테스트

### Backend RAG 테스트
```bash
cd backend
python test_rag.py
```

## 📦 주요 기능

- 🤖 **AI 챗봇**: Claude 3.5를 활용한 대화형 장소 추천
- 🔍 **RAG 검색**: OpenAI 임베딩 + ChromaDB 벡터 검색으로 정확한 시설 추천
- 🗺️ **지도 통합**: 추천 장소를 카카오맵에 표시
- 🌤️ **날씨 연동**: 날씨 정보를 고려한 실내/실외 활동 추천
- 💾 **대화 기억**: 세션별 대화 히스토리 관리

## 📄 라이선스

MIT License
