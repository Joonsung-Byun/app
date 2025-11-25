from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from models.map_models import MapResponse, MapData, MapMarker, MapCenter 
from starlette.concurrency import run_in_threadpool

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
    
    # 1. conversation_id 처리
    conversation_id = request.conversation_id
    if not conversation_id or conversation_id.strip() == "":
        conversation_id = str(uuid.uuid4())
    
    user_message = request.message

    try:
        # 2. 대화 히스토리 로드 및 사용자 메시지 저장
        chat_history = get_conversation_history(conversation_id)
        add_message(conversation_id, "user", user_message)
        
        # RAG 툴 등을 위한 문자열 히스토리 생성
        history_str = "\n\n".join([
            f"[{msg.type.upper()}]\n{msg.content}" 
            for msg in chat_history
        ])
        
        # 3. Agent 실행
        result = await run_in_threadpool(
            agent_executor.invoke,
            {
                "input": user_message,
                "chat_history": chat_history,
                "conversation_history": history_str,
                "child_age": request.child_age,
                "original_query": user_message,
                "conversation_id": conversation_id
            }
        )
        
        output = result["output"]
        intermediate_steps = result.get("intermediate_steps", [])
        
        # -------------------------------------------------------
        # [Step Processing] 툴 실행 결과 후처리
        # -------------------------------------------------------
        for step in intermediate_steps:
            tool_name = getattr(step[0], 'tool', None)
            tool_output = step[1]

            # (A) search_facilities 결과 처리 (RAG)
            if tool_name == "search_facilities":
                try:
                    search_result = json.loads(tool_output)
                    
                    if search_result.get("success"):
                        facilities_data = search_result.get("facilities", [])
                        
                        if facilities_data and len(facilities_data) > 0:
                            save_search_results(conversation_id, facilities_data)
                            add_message(
                                conversation_id, 
                                "search_result", 
                                f"RAG 검색 결과: {facilities_data}"
                            )
                            logger.info(f"✅ RAG 검색 결과 저장: {len(facilities_data)}개 시설")
                        else:
                            logger.info("⚠️ RAG 결과 0건 -> 메모리 덮어쓰기 방지를 위해 저장 안 함")
                            
                except Exception as e:
                    logger.error(f"검색 결과 처리 실패: {e}")

        # -------------------------------------------------------
        # [Response Type A] 신규 지오코딩 툴 결과 (MapResponse 객체 반환)
        # -------------------------------------------------------
        if isinstance(output, MapResponse):
            logger.info("📍 지오코딩 툴에 의한 MapResponse 객체 반환")
            
            # AI 응답 저장 (MapResponse는 add_message 내부에서 안전하게 처리됨)
            add_message(conversation_id, "ai", output)
            
            return ChatResponse(
                conversation_id=conversation_id,
                role="ai",
                type=output.type,       # 'map'
                content=output.content, # "지도를 보여드릴게요" 등
                link=output.link,       # 카카오맵 링크
                data=output.data        # MapData 객체 (center, markers)
            )

        # -------------------------------------------------------
        # [Response Type B] 일반 텍스트 or 기존 RAG 지도 (문자열 반환)
        # -------------------------------------------------------
        else:
            logger.info("💬 일반 텍스트 또는 RAG 지도 처리")
            
            final_output_text = str(output)
            map_data = None
            kakao_link = None
            response_type = "text"

            # RAG 지도 툴(show_map_for_facilities)이 실행되었는지 확인하여 지도 데이터 구성
            for step in intermediate_steps:
                if getattr(step[0], 'tool', None) == "show_map_for_facilities":
                    try:
                        map_result = json.loads(step[1])
                        if map_result.get("success"):
                            facilities = map_result.get("facilities", [])
                            
                            if facilities:
                                logger.info(f"✅ 지도 생성 툴 결과 감지: {len(facilities)}개")
                                
                                # MapMarker 리스트 생성
                                markers = [
                                    MapMarker(
                                        name=f.get("name", "장소"),
                                        lat=float(f.get("lat", 0.0)),
                                        lng=float(f.get("lng", 0.0)),
                                        desc=f.get("desc", "") or f.get("address", "")
                                    )
                                    for f in facilities
                                ]
                                
                                # 중심점 잡기 (첫 번째 시설 기준)
                                if markers:
                                    center_lat = markers[0].lat
                                    center_lng = markers[0].lng
                                    
                                    map_data = MapData(
                                        center=MapCenter(lat=center_lat, lng=center_lng),
                                        markers=markers
                                    )
                                    
                                    kakao_link = f"https://map.kakao.com/link/to/{markers[0].name},{markers[0].lat},{markers[0].lng}"
                                    response_type = "map"

                    except Exception as e:
                        logger.error(f"지도 데이터 구성 실패: {e}")

            # AI 응답 저장
            add_message(conversation_id, "ai", final_output_text)
            
            return ChatResponse(
                conversation_id=conversation_id,
                role="ai",
                type=response_type,
                content=final_output_text,
                link=kakao_link,
                data=map_data
            )
    
    except Exception as e:
        logger.error(f"채팅 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))