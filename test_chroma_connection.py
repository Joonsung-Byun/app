# import chromadb
# from chromadb.config import Settings as ChromaSettings
# from config import settings

# print("ChromaDB 연결 테스트...")
# print(f"Host: {settings.CHROMA_HOST}")
# print(f"Port: {settings.CHROMA_PORT}")
# print(f"Collection: {settings.CHROMA_COLLECTION}")

# try:
#     # 클라이언트 생성
#     client = chromadb.HttpClient(
#         host=settings.CHROMA_HOST,
#         port=settings.CHROMA_PORT,
#         settings=ChromaSettings(anonymized_telemetry=False)
#     )
    
#     print("✅ 클라이언트 생성 성공")
    
#     # 컬렉션 목록
#     collections = client.list_collections()
#     print(f"\n컬렉션 목록 ({len(collections)}개):")
#     for col in collections:
#         print(f"  - {col.name}")
    
#     # 특정 컬렉션 가져오기
#     collection = client.get_collection(settings.CHROMA_COLLECTION)
#     print(f"\n✅ 컬렉션 '{settings.CHROMA_COLLECTION}' 연결 성공")
#     print(f"항목 수: {collection.count()}")
    
#     # 샘플 데이터 1개 가져오기
#     sample = collection.get(limit=1, include=["metadatas", "documents"])
    
#     if sample and sample['ids']:
#         print(f"\n샘플 데이터:")
#         print(f"ID: {sample['ids'][0]}")
#         print(f"메타데이터: {sample['metadatas'][0]}")
#         print(f"문서: {sample['documents'][0][:100]}...")
    
# except Exception as e:
#     print(f"❌ 오류: {e}")
#     import traceback
#     traceback.print_exc()
import chromadb
client = chromadb.HttpClient(host="localhost", port=8000)
### kid_program_collection_pca" 이라는 컬렉션에서 샘플 메타데이터 3개를 출력하는 코드
collection = client.get_collection("kid_program_collection_pca")
sample = collection.get(limit=500, include=["metadatas"])

### 이 컬렉션에 어떤 메타데이터가 있는지 확인 ###

# print("\n🔍 샘플 메타데이터 확인:")
# for i, meta in enumerate(sample["metadatas"]):
#     print(f"[{i+1}] {meta}")

#     name = meta.get('Name', '이름없음')


# for i, meta in enumerate(sample["metadatas"]):
#     name = meta.get('Name', '이름없음')
#     region = meta.get('CTPRVN_NM', '')
#     in_out = meta.get('in_out', '')
#     age = meta.get('Age', '')
#     note = meta.get('Note', age)
#     print(f"[{i+1}] {name} ({region}, {in_out}, 연령: {note})")



