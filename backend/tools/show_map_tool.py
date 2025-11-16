from langchain.tools import tool
from models.chat_models import get_llm
import json
import logging

logger = logging.getLogger(__name__)

@tool
def show_map_for_facilities(conversation_history: str, facility_indices: str = "0,1,2") -> str:
    """
    대화 기록에서 추천된 시설들의 지도 데이터를 생성합니다.
    
    Args:
        conversation_history: 대화 기록 (문자열)
        facility_indices: 표시할 시설 인덱스 (쉼표로 구분)
                         예: "0" = 첫 번째만
                             "1,2" = 두 번째와 세 번째
                             "0,1,2" = 전체 (기본값)
    
    Returns:
        지도 데이터 JSON (name, lat, lng, desc 포함)
    """
    logger.info(f"지도 생성 도구 호출: indices={facility_indices}")
    
    # 인덱스 파싱
    try:
        indices = [int(idx.strip()) for idx in facility_indices.split(",")]
        logger.info(f"요청된 시설 인덱스: {indices}")
    except:
        indices = [0, 1, 2]  # 기본값
        logger.warning(f"인덱스 파싱 실패, 기본값 사용: {indices}")
    
    llm = get_llm()
    
    prompt = f"""
당신은 대화 기록에서 추천된 시설 정보를 정확하게 추출하는 전문가입니다.

**대화 기록:**
{conversation_history}

**작업:**
위 대화에서 AI가 추천한 시설들의 정보를 추출하세요.
모든 추천된 시설을 추출합니다 (최대 10개).

**중요:**
- 시설명(name), 위도(lat), 경도(lng)를 정확히 추출
- 설명(desc)은 간단히 요약 (주소나 특징)
- 추천 순서대로 정렬 (첫 번째 추천 = index 0)
- 대화에서 "첫 번째", "1번", "두 번째", "2번" 등으로 언급된 순서 유지

**응답 형식 (JSON만):**
{{
  "success": true,
  "facilities": [
    {{
      "name": "시설명",
      "lat": 37.5665,
      "lng": 126.9780,
      "desc": "간단한 설명"
    }}
  ]
}}

**대화에 추천된 시설이 없으면:**
{{
  "success": false,
  "facilities": []
}}
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        content = content.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(content)
        
        if result.get("success") and result.get("facilities"):
            all_facilities = result.get("facilities", [])
            
            # 인덱스로 필터링
            filtered_facilities = []
            for idx in indices:
                if 0 <= idx < len(all_facilities):
                    filtered_facilities.append(all_facilities[idx])
                else:
                    logger.warning(f"인덱스 {idx}가 범위를 벗어남 (총 {len(all_facilities)}개)")
            
            if filtered_facilities:
                logger.info(f"✅ 지도 생성 성공: {len(filtered_facilities)}개 시설 (인덱스: {indices})")
                return json.dumps({
                    "success": True,
                    "facilities": filtered_facilities,
                    "selected_indices": indices
                }, ensure_ascii=False)
            else:
                logger.warning("⚠️ 필터링 후 시설이 없음")
                return json.dumps({
                    "success": False,
                    "message": "요청한 인덱스에 해당하는 시설이 없습니다",
                    "facilities": []
                }, ensure_ascii=False)
        else:
            logger.warning("⚠️ 추출된 시설이 없음")
            return json.dumps({
                "success": False,
                "message": "대화에서 추천된 시설을 찾을 수 없습니다",
                "facilities": []
            }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"❌ 지도 생성 실패: {e}")
        return json.dumps({
            "success": False,
            "message": f"지도 생성 중 오류: {str(e)}",
            "facilities": []
        }, ensure_ascii=False)
