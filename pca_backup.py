import chromadb
from chromadb.config import Settings as ChromaSettings
import pandas as pd
import numpy as np
import sys
from time import sleep

# ============================================
# 설정
# ============================================
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "kid_program_collection_pca"

CSV_PATH = "./rag_data_integrated_final.csv"
EMBEDDINGS_PATH = "./embeddings_pca_512-r.npy"  # ← 파일명 수정

print("="*70)
print("🐳 ChromaDB 벡터 데이터 업로드")
print("="*70)
print(f"📁 CSV: {CSV_PATH}")
print(f"📦 임베딩: {EMBEDDINGS_PATH}")
print(f"🔌 ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
print(f"📚 컬렉션: {COLLECTION_NAME}")
print("="*70)

# ============================================
# 1. 파일 확인
# ============================================
import os

if not os.path.exists(CSV_PATH):
    sys.exit(f"❌ CSV 파일이 없습니다: {CSV_PATH}")

if not os.path.exists(EMBEDDINGS_PATH):
    sys.exit(f"❌ 임베딩 파일이 없습니다: {EMBEDDINGS_PATH}")

print("✅ 파일 확인 완료")

# ============================================
# 2. CSV 로드
# ============================================
print("\n📥 CSV 로드 중...")
df = pd.read_csv(CSV_PATH)
df = df.fillna("")
print(f"✅ {len(df)}개 행 로드")

# 메타데이터 컬럼
meta_cols = [
    "Name", "Category1", "Category2", "Category3",
    "Address", "CTPRVN_NM", "SIGNGU_NM",
    "LAT", "LON", "in_out",
    "Age", "age_min", "age_max", "Note"
]
meta_cols = [col for col in meta_cols if col in df.columns]
print(f"📋 메타데이터 컬럼: {meta_cols}")

# ============================================
# 3. 문서 생성
# ============================================
def build_doc(row):
    """시설 정보를 텍스트로 변환"""
    parts = []
    
    if row.get("Name"):
        parts.append(f"시설명: {row['Name']}")
    
    cat1 = row.get("Category1", "")
    cat2 = row.get("Category2", "")
    cat3 = row.get("Category3", "")
    if cat1 or cat2 or cat3:
        parts.append(f"분류: {cat1} / {cat2} / {cat3}")
    
    sido = row.get("CTPRVN_NM", "")
    sigungu = row.get("SIGNGU_NM", "")
    if sido or sigungu:
        parts.append(f"지역: {sido} {sigungu}")
    
    if row.get("Address"):
        parts.append(f"주소: {row['Address']}")
    
    if row.get("Time"):
        parts.append(f"운영시간: {row['Time']}")
    
    if row.get("Day"):
        parts.append(f"운영요일: {row['Day']}")
    
    if row.get("Cost"):
        parts.append(f"이용요금: {row['Cost']}")
    
    if row.get("in_out"):
        parts.append(f"시설 형태: {row['in_out']}")
    
    if row.get("Age"):
        parts.append(f"권장연령: {row['Age']}")
    
    age_min = row.get("age_min")
    age_max = row.get("age_max")
    if age_min or age_max:
        parts.append(f"연령범위: {age_min}~{age_max}세")
    
    if row.get("Note"):
        parts.append(f"추가정보: {row['Note']}")
    
    return ". ".join([p for p in parts if p])

print("\n📝 문서 생성 중...")
documents = df.apply(build_doc, axis=1).tolist()
metadatas = df[meta_cols].to_dict(orient="records")
ids = [f"doc_{i}" for i in range(len(df))]
print(f"✅ {len(documents)}개 문서 구성")

# ============================================
# 4. 임베딩 로드
# ============================================
print("\n📥 임베딩 로드 중...")
embeddings = np.load(EMBEDDINGS_PATH, allow_pickle=True)
print(f"✅ 임베딩 shape: {embeddings.shape}")

# 개수 일치 확인
if len(embeddings) != len(df):
    min_len = min(len(embeddings), len(df))
    print(f"⚠️  CSV({len(df)})와 임베딩({len(embeddings)}) 개수 불일치")
    print(f"→ {min_len}개로 조정")
    documents = documents[:min_len]
    metadatas = metadatas[:min_len]
    ids = ids[:min_len]
    embeddings = embeddings[:min_len]

# ============================================
# 5. ChromaDB 연결
# ============================================
print("\n🔌 ChromaDB 연결 중...")
client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT,
    settings=ChromaSettings(
        anonymized_telemetry=False
    )
)

try:
    client.heartbeat()
    print("✅ 연결 성공")
except Exception as e:
    sys.exit(f"❌ 연결 실패: {e}\n\n도커 컨테이너를 실행하세요:\ndocker run -d -p 8000:8000 chromadb/chroma")

# ============================================
# 6. 기존 컬렉션 삭제 & 재생성
# ============================================
print("\n🗑️  기존 컬렉션 확인...")
collections = [c.name for c in client.list_collections()]

if COLLECTION_NAME in collections:
    print(f"→ '{COLLECTION_NAME}' 삭제 중...")
    client.delete_collection(COLLECTION_NAME)
    sleep(1)
    print("✅ 삭제 완료")
else:
    print("→ 기존 컬렉션 없음")

print(f"\n📚 새 컬렉션 생성: {COLLECTION_NAME}")
collection = client.create_collection(name=COLLECTION_NAME)
print("✅ 생성 완료")

# ============================================
# 7. 데이터 삽입
# ============================================
BATCH_SIZE = 1000
total = len(documents)
print(f"\n🚚 데이터 삽입 시작 (총 {total}개, 배치 {BATCH_SIZE})")

for start in range(0, total, BATCH_SIZE):
    end = min(start + BATCH_SIZE, total)
    
    collection.add(
        ids=ids[start:end],
        documents=documents[start:end],
        metadatas=metadatas[start:end],
        embeddings=embeddings[start:end].tolist()
    )
    
    print(f"   → {end}/{total} 완료 ({(end/total)*100:.1f}%)")

print(f"\n✅ 삽입 완료! 총 {collection.count()}개")

# ============================================
# 8. 샘플 확인
# ============================================
print("\n🔍 샘플 메타데이터 확인:")
sample = collection.get(limit=3, include=["metadatas"])

for i, meta in enumerate(sample["metadatas"]):
    name = meta.get('Name', '이름없음')
    region = meta.get('CTPRVN_NM', '')
    in_out = meta.get('in_out', '')
    age = meta.get('Age', '')
    print(f"[{i+1}] {name} ({region}, {in_out}, 연령: {age})")

print("\n" + "="*70)
print("🎉 ChromaDB 업로드 완료!")
print(f"✅ 컬렉션: {COLLECTION_NAME}")
print(f"✅ 총 {collection.count()}개 문서")
print("="*70)