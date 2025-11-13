from tools.rag_tool import search_facilities
import json

print("="*60)
print("경기도 실외 시설 검색 테스트")
print("="*60)

# 테스트 실행
result = search_facilities.invoke({
    "region": "인천",
    "is_indoor": True,
    "child_age": None,
    "k": 3
})

print("\n" + "="*60)
print("결과")
print("="*60 + "\n")

# JSON 파싱
data = json.loads(result)

# 결과 출력
if data["success"]:
    facilities = data["facilities"]
    print(f"✅ 성공: {len(facilities)}개 시설 찾음\n")
    
    if len(facilities) == 0:
        print("⚠️  조건에 맞는 시설이 없습니다.")
    else:
        for i, f in enumerate(facilities):
            print(f"[{i+1}] {f['name']}")
            print(f"    📍 위치: ({f['lat']}, {f['lng']})")
            print(f"    🏷️  카테고리: {f['category']}")
            print(f"    📝 설명: {f['desc']}")
            print()
else:
    print(f"❌ 실패: {data['message']}")

print("="*60)
