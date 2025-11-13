from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse, MapData, MarkerData
from agent import create_agent
from utils.conversation_memory import (
    get_conversation_history,
    add_message,
    save_search_results,
    get_last_search_results
)
import json
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()
agent_executor = create_agent()

def is_map_request(message: str) -> bool:
    """지도 요청인지 판단"""
    map_keywords = ["지도", "위치", "어디", "map", "show me", "보여줘", "보여주", "지도보여"]
    return any(keyword in message.lower() for keyword in map_keywords)

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 엔드포인트"""
    
    # conversation_id 없으면 생성
    conversation_id = request.conversation_id
    if not conversation_id or conversation_id.strip() == "":
        conversation_id = str(uuid.uuid4())
        logger.info(f"새 conversation_id 생성: {conversation_id}")
    
    user_message = request.message
    
    logger.info(f"=== 채팅 요청: {conversation_id} ===")
    logger.info(f"메시지: {user_message}")
    
    try:
        # 대화 히스토리 가져오기
        chat_history = get_conversation_history(conversation_id)
        
        # 사용자 메시지 추가
        add_message(conversation_id, "user", user_message)
        
        # 지도 요청인지 확인
        if is_map_request(user_message):
            logger.info("지도 요청 감지")
            
            # 이전 검색 결과 가져오기
            last_results = get_last_search_results(conversation_id)
            
            if last_results and len(last_results) > 0:
                logger.info(f"저장된 검색 결과 사용: {len(last_results)}개")
                
                # 지도 응답 생성
                markers = [
                    MarkerData(
                        name=f["name"],
                        lat=f["lat"],
                        lng=f["lng"],
                        desc=f.get("desc", "")
                    )
                    for f in last_results
                ]
                
                center_lat = sum(m.lat for m in markers) / len(markers)
                center_lng = sum(m.lng for m in markers) / len(markers)
                
                map_data = MapData(
                    center={"lat": center_lat, "lng": center_lng},
                    markers=markers
                )
                
                kakao_link = f"https://map.kakao.com/link/to/{markers[0].name},{markers[0].lat},{markers[0].lng}"
                
                add_message(conversation_id, "ai", "[지도 데이터 전송]")
                
                return ChatResponse(
                    role="ai",
                    content="",
                    type="map",
                    link=kakao_link,
                    data=map_data,
                    conversation_id=conversation_id
                )
            else:
                logger.warning("저장된 검색 결과 없음")
                
                ai_response = "아직 장소를 검색하지 않았어요. 먼저 원하시는 지역과 활동을 말씀해주세요!"
                add_message(conversation_id, "ai", ai_response)
                
                return ChatResponse(
                    role="ai",
                    content=ai_response,
                    type="text",
                    conversation_id=conversation_id
                )
        
        # 일반 요청 - Agent 실행 (original_query 전달)
        result = agent_executor.invoke({
            "input": user_message,
            "chat_history": chat_history,
            "child_age": request.child_age,
            "original_query": user_message  # ← 추가
        })
        
        output = result["output"]
        intermediate_steps = result.get("intermediate_steps", [])
        
        # facilities 추출
        facilities_data = None
        for step in intermediate_steps:
            if step[0].tool == "search_facilities":
                try:
                    search_result = json.loads(step[1])
                    if search_result.get("success"):
                        facilities_data = search_result.get("facilities", [])
                        
                        if facilities_data:
                            save_search_results(conversation_id, facilities_data)
                except:
                    pass
        
        # AI 응답 저장
        add_message(conversation_id, "ai", output)
        
        # 응답 생성 (항상 type: text)
        return ChatResponse(
            role="ai",
            content=output,
            type="text",
            conversation_id=conversation_id
        )
    
    except Exception as e:
        logger.error(f"채팅 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    
    ## 동작 예시

    ### 입력: "부산 자전거 타기 좋은 곳"
    # ```
    # 1. chat.py
    # → original_query = "부산 자전거 타기 좋은 곳"
    
    # 2. Agent 실행
    # → extract_user_intent("부산 자전거 타기 좋은 곳")
    # → {"location": "부산", "needs_weather_check": true}
    
    # 3. get_weather_forecast("부산", "today")
    # → {"is_indoor": false}
    
    # 4. search_facilities(
    #         region="부산",
    #         is_indoor=False,
    #         original_query="부산 자전거 타기 좋은 곳"  ← 핵심!
    #     )
    
    # 5. rag_tool.py
    # → query_text = "부산 실외 부산 자전거 타기 좋은 곳"
    # → 임베딩 검색으로 자전거 관련 시설 우선 반환!
    # ```