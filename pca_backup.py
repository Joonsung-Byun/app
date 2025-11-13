import chromadb
import pandas as pd
import numpy as np
import os
import sys
from time import sleep

# ============================================
# 1️⃣ 기본 설정
# ============================================
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "kid_program_collection_pca"  # ✅ FastAPI 설정과 동일하게
CSV_PATH = "./rag_data_integrated_final.csv"
EMB_PATH = "./embeddings_pca_512.npy"

print("="*70)
print("🌱 ChromaDB 컬렉션 복구 스크립트 (512차원 PCA)")
print("="*70)
print(f"📁 CSV 파일: {CSV_PATH}")
print(f"📦 임베딩 파일: {EMB_PATH}")
print(f"📚 컬렉션 이름: {COLLECTION_NAME}")
print(f"🔌 연결: {CHROMA_HOST}:{CHROMA_PORT}")
print("="*70)

# ============================================
# 2️⃣ 파일 확인
# ============================================
if not os.path.exists(CSV_PATH):
    sys.exit(f"❌ CSV 파일을 찾을 수 없습니다: {CSV_PATH}")
if not os.path.exists(EMB_PATH):
    sys.exit(f"❌ 임베딩 파일을 찾을 수 없습니다: {EMB_PATH}")

# ============================================
# 3️⃣ CSV 로드
# ============================================
print("\n📥 CSV 로드 중...")
df = pd.read_csv(CSV_PATH)
print(f"✅ {len(df)}개 행 로드 완료")

df = df.fillna("")  # NaN 방지

# ✅ Age 컬럼 포함 (텍스트 기반)
meta_cols = [
    "Name", "Category1", "Category2", "Category3",
    "Address", "CTPRVN_NM", "SIGNGU_NM",
    "LAT", "LON", "in_out",
    "Age", "age_min", "age_max"
]
meta_cols = [col for col in meta_cols if col in df.columns]

print(f"📋 사용될 메타데이터 컬럼: {meta_cols}")

# ============================================
# 4️⃣ 문서(text) 구성
# ============================================
def build_doc(row):
    parts = []
    if row.get("Name"): parts.append(f"시설명: {row['Name']}")
    if row.get("Category1"): parts.append(f"분류: {row['Category1']} / {row.get('Category2','')} / {row.get('Category3','')}")
    if row.get("CTPRVN_NM"): parts.append(f"지역: {row['CTPRVN_NM']} {row.get('SIGNGU_NM','')}")
    if row.get("Address"): parts.append(f"주소: {row['Address']}")
    if row.get("Age"): parts.append(f"연령: {row['Age']}")
    return ". ".join([p for p in parts if p])

print("\n📝 문서 생성 중...")
documents = df.apply(build_doc, axis=1).tolist()
metadatas = df[meta_cols].to_dict(orient="records")
ids = [f"doc_{i}" for i in range(len(df))]
print(f"✅ {len(documents)}개 문서 구성 완료")

# ============================================
# 5️⃣ 임베딩 로드
# ============================================
print("\n📥 임베딩 로드 중...")
embs = np.load(EMB_PATH, allow_pickle=True)
print(f"✅ 임베딩 shape: {embs.shape}")

if len(embs) != len(df):
    min_len = min(len(embs), len(df))
    print(f"⚠️ CSV({len(df)})와 임베딩({len(embs)}) 개수 불일치 → {min_len}개로 조정")
    documents, metadatas, ids, embs = documents[:min_len], metadatas[:min_len], ids[:min_len], embs[:min_len]

# ============================================
# 6️⃣ Chroma 연결
# ============================================
print("\n🔌 ChromaDB 연결 중...")
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
try:
    client.heartbeat()
    print("✅ 연결 성공")
except Exception as e:
    sys.exit(f"❌ 연결 실패: {e}\n도커 컨테이너를 실행 중인지 확인하세요.")

# ============================================
# 7️⃣ 기존 컬렉션 삭제 & 재생성
# ============================================
print("\n🗑️ 기존 컬렉션 확인 중...")
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
# 8️⃣ 데이터 삽입
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
        embeddings=embs[start:end].tolist()
    )
    print(f"   → {end}/{total} 완료 ({(end/total)*100:.1f}%)")

print("\n🎉 삽입 완료!")
print(f"총 문서 수: {collection.count()}")

# ============================================
# 9️⃣ 샘플 확인
# ============================================
print("\n🔍 샘플 메타데이터 확인:")
sample = collection.get(limit=3, include=["metadatas"])
for i, meta in enumerate(sample["metadatas"]):
    print(f"[{i+1}] {meta.get('Name','이름없음')} ({meta.get('CTPRVN_NM','')}, {meta.get('in_out','')}, 연령: {meta.get('Age','')})")

print("\n✅ PCA(512차원) 컬렉션 복구 완료!")
print(f"✅ 이름: {COLLECTION_NAME}")
print("="*70)
