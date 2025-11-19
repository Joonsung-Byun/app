from langchain.tools import tool
from models.chat_models import get_llm
from utils.conversation_memory import get_conversation_history
import json
import logging

logger = logging.getLogger(__name__)

@tool
def show_map_for_facilities(
    conversation_id: str,
    facility_indices: str = "0,1,2"
) -> str:
    """
    대화 기록에서 추천된 시설들의 지도 데이터를 생성합니다.
    
    Args:
        conversation_id: 현재 대화 ID
        facility_indices: 표시할 시설 인덱스 (쉼표로 구분)
                         예: "0" = 첫 번째만
                             "1,2" = 두 번째와 세 번째
                             "0,1,2" = 전체 (기본값)
    
    Returns:
        지도 데이터 JSON (name, lat, lng, desc 포함)
    """
    if not conversation_id:
        logger.error("❌ conversation_id를 찾을 수 없음")
        return json.dumps({
            "success": False,
            "message": "대화 세션을 찾을 수 없습니다",
            "facilities": []
        }, ensure_ascii=False)
    
    logger.info(f"지도 생성 도구 호출: conversation_id={conversation_id}, indices={facility_indices}")
    
    # 인덱스 파싱
    try:
        indices = [int(idx.strip()) for idx in facility_indices.split(",")]
        logger.info(f"요청된 시설 인덱스: {indices}")
    except:
        indices = [0, 1, 2]  # 기본값
        logger.warning(f"인덱스 파싱 실패, 기본값 사용: {indices}")
    
    # conversation_id로 직접 히스토리 가져오기
    chat_history = get_conversation_history(conversation_id)
    
    # 문자열로 변환
    history_str = "\n\n".join([
        f"[{msg.type.upper()}]\n{msg.content}" 
        for msg in chat_history
    ])
    
    print("show_map에서 보는 conversation_id:", conversation_id)
    print("show_map에서 보는 chat_history 메시지 수:", len(chat_history))
    
    llm = get_llm()
    
    prompt = f"""
당신은 대화 기록에서 **가장 최근에** 추천된 시설 정보를 정확하게 추출하는 전문가입니다.

**대화 기록:**
{history_str}

**작업:**
1. 위 대화를 **시간 순서대로** 읽으세요 (위에서 아래로)
2. **가장 마지막에 등장한** "마지막 검색 결과:"를 찾으세요
3. 그 검색 결과의 JSON list에서 **정확히** 시설 정보를 추출하세요
4. **이전 검색 결과는 무시**하고, 오직 가장 최근 것만 사용하세요

**중요 규칙:**
- "마지막 검색 결과:"가 여러 번 나온다면, **가장 아래(최신)의 것만** 사용
- lat/lng는 **반드시** JSON list에서 그대로 복사
- 시설명(name), 위도(lat), 경도(lng)를 정확히 추출
- 설명(desc)은 간단히 요약
- 추천 순서대로 정렬 (첫 번째 추천 = index 0)

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

**검색 결과가 없으면:**
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
