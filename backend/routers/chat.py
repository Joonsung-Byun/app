from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse, MapData, MarkerData
from agent import create_agent
from utils.conversation_memory import (
    get_conversation_history,
    add_message,
    save_search_results
)
import json
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()
agent_executor = create_agent()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 엔드포인트"""
    
    # conversation_id 없으면 생성
    conversation_id = request.conversation_id
    
    if not conversation_id or conversation_id.strip() == "":
        conversation_id = str(uuid.uuid4())
    
    user_message = request.message

    
    try:
        # 대화 히스토리 가져오기
        chat_history = get_conversation_history(conversation_id)
        
        # 사용자 메시지 추가
        add_message(conversation_id, "user", user_message)
        
        # role에 상관없는 모든 대화 기록 문자열 생성
        history_str = "\n\n".join([
            f"[{msg.type.upper()}]\n{msg.content}" 
            for msg in chat_history
        ])
        
        # Agent 실행 (모든 요청 처리)
        result = agent_executor.invoke({
            "input": user_message,
            "chat_history": chat_history,
            "conversation_history": history_str,  # show_map_for_facilities용
            "child_age": request.child_age,
            "original_query": user_message,
            "conversation_id": conversation_id
        })
        
        output = result["output"]
        intermediate_steps = result.get("intermediate_steps", [])
        
        # search_facilities 결과 저장
        for step in intermediate_steps:
            if step[0].tool == "search_facilities":
                try:
                    search_result = json.loads(step[1])
                    if search_result.get("success"):
                        facilities_data = search_result.get("facilities", [])
                        if facilities_data:
                            save_search_results(conversation_id, facilities_data)
                            add_message(
                            conversation_id, 
                            "search_result", 
                            f"마지막 검색 결과: {facilities_data}"
                        )
                            logger.info(f"✅ 검색 결과 저장: {len(facilities_data)}개 시설")
                except Exception as e:
                    logger.error(f"검색 결과 저장 실패: {e}")
        
        # show_map_for_facilities 결과 처리
        map_data = None
        kakao_link = None
        response_type = "text"
        
        for step in intermediate_steps:
            if step[0].tool == "show_map_for_facilities":
                try:
                    map_result = json.loads(step[1])
                    if map_result.get("success"):
                        facilities = map_result.get("facilities", [])
                        selected_indices = map_result.get("selected_indices", [0, 1, 2])
                        
                        if facilities and len(facilities) > 0:
                            logger.info(f"✅ 지도 데이터 생성: {len(facilities)}개 시설 (인덱스: {selected_indices})")
                            
                            # MarkerData 생성 (필터링된 시설만)
                            markers = [
                                MarkerData(
                                    name=f["name"],
                                    lat=f["lat"],
                                    lng=f["lng"],
                                    desc=f.get("desc", "")
                                )
                                for f in facilities
                            ]
                            
                            # 필터링된 첫 번째 시설을 중심으로
                            # (예: 인덱스 [1,2] 선택 시 → 두 번째 시설이 중심)
                            center_lat = markers[0].lat
                            center_lng = markers[0].lng
                            
                            map_data = MapData(
                                center={"lat": center_lat, "lng": center_lng},
                                markers=markers
                            )
                            
                            # 카카오맵 링크도 필터링된 첫 번째 시설
                            kakao_link = f"https://map.kakao.com/link/to/{markers[0].name},{markers[0].lat},{markers[0].lng}"
                            
                            response_type = "map"
                            
                            # 지도 응답 메시지
                            if len(facilities) == 1:
                                output = f"{markers[0].name}의 지도를 표시합니다."
                            else:
                                output = f"{len(facilities)}개 시설의 지도를 표시합니다."
                            
                except Exception as e:
                    logger.error(f"지도 데이터 처리 실패: {e}")
        
        # AI 응답 저장
        add_message(conversation_id, "ai", output)
        
        # 응답 생성
        return ChatResponse(
            role="ai",
            content=output,
            type=response_type,
            link=kakao_link,
            data=map_data,
            conversation_id=conversation_id
        )
    
    except Exception as e:
        logger.error(f"채팅 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
