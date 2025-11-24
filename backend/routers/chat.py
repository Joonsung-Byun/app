from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from models.map_models import MapResponse, MapData, MapMarker, MapCenter 

from agent import create_agent
from utils.conversation_memory import (
    get_conversation_history,
    add_message,
    save_search_results,
    set_status,
    get_status,
)
import json
import logging
import uuid
import asyncio

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
    # 초기 상태: 사용자 의도 파악 중
    set_status(conversation_id, "요청 분석 중..")

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
        # invoke 결과의 output은 '문자열'일 수도 있고, 'MapResponse 객체'일 수도 있습니다.
        # 👉 CPU/IO 작업을 별도 스레드에서 돌려서, /chat/status 폴링 요청이 동시에 처리될 수 있게 함.
        result = await asyncio.to_thread(
            agent_executor.invoke,
            {
                "input": user_message,
                "chat_history": chat_history,
                "conversation_history": history_str,
                "child_age": request.child_age,
                "original_query": user_message,
                "conversation_id": conversation_id,
            },
        )
        
        output = result["output"]
        intermediate_steps = result.get("intermediate_steps", [])
        
        # -------------------------------------------------------
        # [공통] search_facilities 결과 저장 (RAG 컨텍스트용)
        # -------------------------------------------------------
        for step in intermediate_steps:
            if getattr(step[0], 'tool', None) == "search_facilities":
                try:
                    # step[1]은 툴의 리턴값(JSON string)
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

        # -------------------------------------------------------
        # [Case A] 신규 지오코딩 툴 결과 (MapResponse 객체 반환)
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
        # [Case B] 일반 텍스트 or 기존 RAG 지도 (문자열 반환)
        # -------------------------------------------------------
        else:
            logger.info("💬 일반 텍스트 또는 RAG 지도 처리")
            
            final_output_text = str(output)
            map_data = None
            kakao_link = None
            response_type = "text"

            # RAG 지도 툴(show_map_for_facilities)이 실행되었는지 확인
            for step in intermediate_steps:
                if getattr(step[0], 'tool', None) == "show_map_for_facilities":
                    try:
                        map_result = json.loads(step[1])
                        if map_result.get("success"):
                            facilities = map_result.get("facilities", [])
                            # selected_indices = map_result.get("selected_indices", [0, 1, 2]) # 필요시 사용
                            
                            if facilities:
                                logger.info(f"✅ RAG 지도 데이터 생성: {len(facilities)}개")
                                
                                # MapMarker 리스트 생성
                                markers = [
                                    MapMarker(
                                        name=f["name"],
                                        lat=float(f["lat"]),
                                        lng=float(f["lng"]),
                                        desc=f.get("desc", "")
                                    )
                                    for f in facilities
                                ]
                                
                                # 중심점 잡기 (첫 번째 시설 기준)
                                center_lat = markers[0].lat
                                center_lng = markers[0].lng
                                
                                map_data = MapData(
                                    center=MapCenter(lat=center_lat, lng=center_lng),
                                    markers=markers
                                )
                                
                                kakao_link = f"https://map.kakao.com/link/to/{markers[0].name},{markers[0].lat},{markers[0].lng}"
                                response_type = "map"
                                
                                # 텍스트 메시지가 너무 단순하면 보완 (선택 사항)
                                if not final_output_text:
                                    final_output_text = f"{len(facilities)}개 시설의 위치를 지도에 표시합니다."

                    except Exception as e:
                        logger.error(f"RAG 지도 데이터 처리 실패: {e}")

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


@router.get("/chat/status/{conversation_id}")
async def chat_status(conversation_id: str):
    """
    현재 대화(conversation_id)의 진행 상태 텍스트를 반환하는 엔드포인트.
    프론트엔드는 이 값을 주기적으로 폴링해서
    '날씨 확인 중..', '시설 검색 중..' 같은 실제 상태를 표시할 수 있다.
    """
    status = get_status(conversation_id)
    return {"conversation_id": conversation_id, "status": status or ""}
