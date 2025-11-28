from langchain.tools import tool
from models.chat_models import get_llm  # 수정
from datetime import datetime
import json

@tool
def extract_user_intent(user_message: str) -> str:
    """
    사용자 메시지에서 지역, 날씨 조건, 날짜 정보를 추출합니다.
    
    Args:
        user_message: 사용자 메시지
    
    Returns:
        JSON 문자열
    """
    llm = get_llm()
    
    # 현재 날짜 정보
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    weekday = today.strftime("%A")
    
    prompt = f"""
당신은 사용자 메시지를 분석하는 전문가입니다.
현재 날짜: {today_str} ({weekday})

사용자 메시지: "{user_message}"

위 메시지에서 다음 정보를 추출하세요:

1. **location (지역명)**: 
   - 서울, 부산, 경기, 수원, 순천, 제주 등
   - 없으면 null

2. **weather_mentioned (날씨 언급 여부)**:
   - "비", "맑은", "흐린" 등 날씨 관련 키워드 있으면 true
   - 없거나 유저가 날씨 확인 해달라고 하면 false

3. **weather_condition (날씨 상태)**:
   - "비", "맑음", "흐림", "눈" 등
   - 없으면 null

4. **date (날짜)**:
   - "오늘" → "today"
   - "내일" → "tomorrow"
   - "주말" → "this_weekend"
   - "토요일" → 가장 가까운 토요일 YYYY-MM-DD
   - 언급 없으면 "today"

5. **needs_weather_check**:
   - weather_mentioned가 false이면 true
   - weather_mentioned가 true이면 false
   - 단순 시설 유무를 묻는 질문에는 무조건 false 예) "서울 탁구장 있어?" -> false

**응답 형식 (JSON만):**
{{
  "location": "지역명 or null",
  "weather_mentioned": true or false,
  "weather_condition": "날씨 or null",
  "date": "날짜 or today",
  "needs_weather_check": true or false
}}
"""
    
    response = llm.invoke(prompt)
    
    try:
        content = response.content if hasattr(response, 'content') else str(response)
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        # 기본값
        return json.dumps({
            "location": None,
            "weather_mentioned": False,
            "weather_condition": None,
            "date": "today",
            "needs_weather_check": True
        }, ensure_ascii=False)