"""
RAG 시스템 테스트 스크립트
OpenAI text-embedding-3-large 모델을 사용한 시설 검색 테스트
"""

from tools.rag_tool import search_facilities
import json

def test_search_facilities():
    """시설 검색 테스트"""
    
    # 테스트 케이스들
    test_queries = [
        "부산 자전거 타기 좋은 곳",
        "서울 실내 놀이터",
        "창원 아이와 갈만한 공원",
        "수도권 배드민턴 프로그램"
    ]
    
    print("=" * 60)
    print("RAG 시설 검색 테스트 시작")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"🔍 검색 쿼리: {query}")
        print(f"{'='*60}\n")
        
        try:
            # search_facilities 호출 (위치 인자로 전달!)
            result_json = search_facilities.invoke({
                "original_query": query,
                "conversation_id": f"test-{query}",
                "k": 5
            })
            result = json.loads(result_json)
            
            if result.get("success"):
                facilities = result.get("facilities", [])
                print(f"✅ 검색 성공! {len(facilities)}개 시설 발견\n")
                
                for idx, facility in enumerate(facilities, 1):
                    print(f"[{idx}] {facility['name']}")
                    print(f"    📍 위치: ({facility['lat']}, {facility['lng']})")
                    print(f"    📁 카테고리: {facility['category']}")
                    print(f"    📝 설명: {facility['desc'][:50]}...")
                    print(f"    📊 유사도: {facility['distance']:.4f}")
                    print(f"특이사항: {facility.get('note', '없음')}")
                    print()
            else:
                print(f"❌ 검색 실패: {result.get('message')}")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    print("\n🚀 OpenAI text-embedding-3-large 모델 사용")
    print("📊 ChromaDB 벡터 검색 테스트\n")
    
    test_search_facilities()
    
    print("\n✅ 테스트 완료!")
