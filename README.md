# Kids Chatbot - 가족 나들이 추천 챗봇 - v2

Monorepo 구조로 Backend(FastAPI)와 Frontend(React)를 관리합니다.

## 📁 프로젝트 구조

```
kids-chatbot/
├── backend/         # FastAPI + LangChain + ChromaDB + OpenAI
├── frontend/        # React + TypeScript + Kakao Map API
├── evaluation/      # 평가 스크립트 (backend 의존성 필요)
└── docker-compose.yml
```

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI
- **LLM**: QWEN3-8B-instruction
- **Embeddings**: OpenAI text-embedding-3-large
- **Vector DB**: ChromaDB
- **Agent Framework**: LangChain

### Frontend
- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **Map**: Kakao Map API

## 🚀 실행 방법

### 방법 1: Docker Compose 사용 (권장)

```bash
# 환경 변수 설정 (.env 파일 생성)
cp .env.example .env  # .env 파일을 생성하고 API 키 입력

# 전체 서비스 실행 (backend + frontend + chromadb)
docker compose up --build

# 백그라운드 실행
docker compose up -d --build

# 서비스 종료
docker compose down
```

**중요**: Docker 사용 시 별도로 `pip install` 할 필요 없음!
- Dockerfile이 자동으로 requirements.txt 설치
- 의존성이 변경되지 않으면 Docker 캐시로 빠르게 재사용

### 방법 2: 로컬 개발 환경

#### Backend

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 의존성 설치 (evaluation 스크립트도 이 의존성 사용)
pip install -r requirements.txt

# 서버 실행
python run.py
# 또는
uvicorn main:app --reload --port 8080
```

#### Frontend

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

#### ChromaDB (별도 실행 필요)

```bash
# Docker로 ChromaDB만 실행
docker run -d -p 8000:8000 -v ./backend/chroma_data:/data chromadb/chroma:latest
```

## 📝 환경 변수 설정

### Backend (.env)
```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
KAKAO_API_KEY=your_kakao_api_key
OPENWEATHER_API_KEY=your_weather_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
PERPLEXITY_API_KEY=your_perplexity_api_key

# LLM Backend 선택
LLM_BACKEND=openai  # 또는 vllm
VLLM_ENDPOINT=http://localhost:8001  # vLLM 사용 시
VLLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct  # vLLM 모델명

# ChromaDB
CHROMA_HOST=chromadb  # Docker 사용 시, 로컬은 localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=kid_program_collection
```
- `PERPLEXITY_API_KEY`: Perplexity 기반 웹 검색(naver_web_search)에 필요합니다.  
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET`: 맘카페 검색(naver_cafe_search)에서 사용합니다.

### Frontend (.env.local)
```env
VITE_API_URL=http://localhost:8080
VITE_KAKAO_MAP_API_KEY=your_kakao_map_api_key
```

## 🧪 테스트 및 평가

### Backend RAG 테스트
```bash
cd backend
python test_rag.py
```

### Evaluation 스크립트 실행
```bash
# backend 의존성이 먼저 설치되어 있어야 함
cd evaluation
python evaluate_rag.py  # 또는 다른 평가 스크립트
```

## 📦 주요 기능

- 🤖 **AI 챗봇**: Qwen3-8B-instruction or OpenAI GPT-5 API를 활용한 대화형 장소 추천
- 🔍 **RAG 검색**: OpenAI 임베딩 + ChromaDB 벡터 검색으로 정확한 시설 추천
- 🗺️ **지도 통합**: 추천 장소를 카카오맵에 표시
- 🌤️ **날씨 연동**: 날씨 정보를 고려한 실내/실외 활동 추천
- 💾 **대화 기억**: 세션별 대화 히스토리 관리
- 🖥 **웹 검색**: Perplexity 기반 최근 이벤트 및 행사 정보

## 📄 라이선스

MIT License
