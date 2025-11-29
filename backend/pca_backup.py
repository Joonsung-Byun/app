import os
import pandas as pd
import numpy as np
import chromadb
from chromadb.config import Settings as ChromaSettings
from dotenv import load_dotenv
from time import sleep
import openai

# ============================================
# 환경변수
# ============================================
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ============================================
# 설정
# ============================================
# 도커 내에서는 서비스명 chromadb, 호스트에서 직접 실행 시에는 localhost로 접근
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "kid_program_collection_v2")

CSV_PATH = "./rag_data_integrated_final_rev_loc_inout_fixed_final.csv"

# OpenAI 임베딩 모델 선택
EMB_MODEL = "text-embedding-3-large"    # 3072차원 (추천)
# EMB_MODEL = "text-embedding-3-small"  # 1536차원 (비용↓)

print("="*70)
print("🔥 Kids Program RAG - ChromaDB 벡터 데이터 업로드")
print("="*70)
print(f"📁 CSV: {CSV_PATH}")
print(f"🔌 ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
print(f"📚 컬렉션: {COLLECTION_NAME}")
print("="*70)

# ============================================
# 1. 파일 확인
# ============================================
if not os.path.exists(CSV_PATH):
    raise SystemExit(f"❌ CSV 파일 없음: {CSV_PATH}")

print("✅ CSV 파일 확인 완료")

# ============================================
# 2. CSV 로드
# ============================================
print("\n📥 CSV 로드 중...")
df = pd.read_csv(CSV_PATH).fillna("")
print(f"✅ 총 {len(df)}개 행 로드 완료")

# ============================================
# 3. 문서(document) 생성 함수 (임베딩 내용)
# ============================================
def build_doc(row):
    parts = []

    # 1) 시설명
    if row.get("Name"):
        parts.append(f"시설명: {row['Name']}")

    # 2) 분류 Category1~3
    cats = [row.get("Category1",""), row.get("Category2",""), row.get("Category3","")]
    cats = [c for c in cats if c]
    if cats:
        parts.append("분류: " + ", ".join(cats))

    # 3) 행정동/시군구
    if row.get("CTPRVN_NM") or row.get("SIGNGU_NM"):
        parts.append(f"지역: {row['CTPRVN_NM']} {row['SIGNGU_NM']}")

    # 4) 주소
    if row.get("Address"):
        parts.append(f"주소: {row['Address']}")

    # 5) 운영시간
    if row.get("Time"):
        parts.append(f"운영시간: {row['Time']}")

    # 6) 운영요일
    if row.get("Day"):
        parts.append(f"운영요일: {row['Day']}")

    # 7) 비용
    if row.get("Cost"):
        parts.append(f"이용요금: {row['Cost']}")

    # 8) 실내/실외
    if row.get("in_out"):
        parts.append(f"실내/실외: {row['in_out']}")

    # 9) 권장연령 (자연어로 의미 있으므로 포함)
    if row.get("Age"):
        parts.append(f"권장연령: {row['Age']}")

    # 10) 자유 텍스트 Note
    if row.get("Note"):
        parts.append(f"추가설명: {row['Note']}")

    return "\n".join(parts)

print("\n📝 문서 생성 중...")
documents = df.apply(build_doc, axis=1).tolist()
print(f"✅ 문서 {len(documents)}개 생성")

# ============================================
# 4. 메타데이터 구성 (필터링/정렬용)
# ============================================
META_COLS = [
    "Name", "Category1", "Category2", "Category3",
    "Address", "CTPRVN_NM", "SIGNGU_NM",
    "LAT", "LON", "in_out",
    "Age", "age_min", "age_max",
    "Time", "Day", "Cost",
    "Note"
]

META_COLS = [c for c in META_COLS if c in df.columns]
metadatas = df[META_COLS].to_dict(orient="records")

ids = [f"doc_{i}" for i in range(len(df))]

print(f"📋 메타데이터 컬럼: {META_COLS}")

# ============================================
# 5. ChromaDB 연결
# ============================================
print("\n🔌 ChromaDB 연결 중...")
client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT,
    settings=ChromaSettings(anonymized_telemetry=False)
)
print("✅ 연결 성공!")

# 기존 컬렉션 삭제
existing = [c.name for c in client.list_collections()]
if COLLECTION_NAME in existing:
    print(f"🗑 기존 컬렉션 '{COLLECTION_NAME}' 삭제 중...")
    client.delete_collection(COLLECTION_NAME)
    sleep(1)
    print("   → 삭제 완료")

# 새 컬렉션 생성
print(f"📚 새 컬렉션 생성: {COLLECTION_NAME}")
collection = client.create_collection(COLLECTION_NAME)

# ============================================
# 6. OpenAI 임베딩 + 데이터 삽입
# ============================================
print("\n🚀 벡터 임베딩 + Chroma 업로드 시작")

BATCH = 100
total = len(documents)

for start in range(0, total, BATCH):
    end = min(start + BATCH, total)
    
    batch_docs = documents[start:end]

    # ---- OpenAI Embedding 호출 ----
    try:
        res = openai.embeddings.create(
            model=EMB_MODEL,
            input=batch_docs
        )
    except Exception as e:
        print(f"❌ OpenAI 에러 발생: {e}")
        sleep(2)
        continue

    embeddings = [item.embedding for item in res.data]

    # ---- Chroma 업로드 ----
    collection.add(
        ids=ids[start:end],
        documents=batch_docs,
        metadatas=metadatas[start:end],
        embeddings=embeddings
    )

    print(f"   → {end}/{total} ({(end/total)*100:.1f}%) 완료")

    sleep(0.3)  # Rate-limit 완화

print("\n🎉 모든 데이터 업로드 완료!")

# ============================================
# 7. 샘플 조회 (문서 + 메타데이터)
# ============================================
print("\n🔍 샘플 문서/메타데이터 출력")

sample = collection.get(limit=3, include=["documents", "metadatas"])

for idx in range(len(sample["documents"])):
    print("\n-----------------------------------")
    print(f"[{idx+1}] 문서:")
    print(sample["documents"][idx])
    print("\n메타데이터:")
    print(sample["metadatas"][idx])

print("\n" + "="*70)
print("🎉 ChromaDB 임베딩 업로드 완료!")
print(f"📚 컬렉션 이름: {COLLECTION_NAME}")
print(f"📌 총 문서 수: {collection.count()}")
print("="*70)
