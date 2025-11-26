from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest, ChatResponse, ChatStatusResponse
from models.map_models import MapResponse, MapData, MapMarker, MapCenter 
from agent import create_agent
from utils.conversation_memory import (
    get_conversation_history,
    add_message,
    save_search_results,
    get_status,
    set_status,
    get_last_search_results,
)
import json
import logging
import uuid
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
agent_executor = create_agent()


@router.get("/chat/status/{conversation_id}", response_model=ChatStatusResponse)
async def chat_status(conversation_id: str):
    """대화 상태 조회 엔드포인트 (프론트 폴링용)"""
    return ChatStatusResponse(
        conversation_id=conversation_id,
        status=get_status(conversation_id)
    )

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 엔드포인트"""
    
    # 1. conversation_id 처리
    conversation_id = request.conversation_id
    if not conversation_id or conversation_id.strip() == "":
        conversation_id = str(uuid.uuid4())
    # 신규 요청 시작 상태 초기화
    set_status(conversation_id, "질문 분석 중...")
    
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
        
        # 3. Agent 실행 (⚡️ 완전 비동기 실행)
        result = await agent_executor.ainvoke({
            "input": user_message,
            "chat_history": chat_history,
            "conversation_history": history_str,
            "child_age": request.child_age,
            "original_query": user_message,
            "conversation_id": conversation_id
        })
        
        output = result["output"]
        intermediate_steps = result.get("intermediate_steps", [])
        
        # -------------------------------------------------------
        # [Step Processing] 툴 실행 결과 후처리
        # -------------------------------------------------------
        map_response_from_tool = None
        show_map_tool_executed = False
        last_results = get_last_search_results(conversation_id)
        last_results = get_last_search_results(conversation_id)

        for step in intermediate_steps:
            tool_name = getattr(step[0], 'tool', None)
            tool_output = step[1]

            # (A) search_facilities 결과 처리 (RAG)
            if tool_name == "search_facilities":
                try:
                    # 문자열이 JSON 구조가 아닐 수 있으므로 안전하게 파싱
                    if isinstance(tool_output, str):
                        stripped = tool_output.strip()
                        if not (stripped.startswith("{") or stripped.startswith("[")):
                            raise ValueError("non-json output")
                        search_result = json.loads(stripped)
                    else:
                        search_result = json.loads(str(tool_output))
                    
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
            
            # (B) search_map_by_address 결과가 MapResponse 객체로 온 경우 캐싱 (return_direct 실패 대비)
            if tool_name == "search_map_by_address" and isinstance(tool_output, MapResponse):
                map_response_from_tool = tool_output
            
            if tool_name == "show_map_for_facilities":
                show_map_tool_executed = True

        # -------------------------------------------------------
        # [Response Type A] 지도 응답 처리 (MapResponse 객체 우선)
        # -------------------------------------------------------
        map_output = None

        # 1) 에이전트가 직접 MapResponse를 반환한 경우
        if isinstance(output, MapResponse):
            map_output = output
        # 2) 직전 RAG 결과가 있고 show_map_for_facilities가 실행되지 않았다면 RAG 좌표 기반으로 지도 생성
        elif last_results and not show_map_tool_executed:
            markers = []
            for fac in last_results:
                try:
                    lat = float(fac.get("lat", 0.0))
                    lng = float(fac.get("lng", 0.0))
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0
                if lat == 0.0 and lng == 0.0:
                    continue
                markers.append(
                    MapMarker(
                        name=fac.get("name", "장소"),
                        lat=lat,
                        lng=lng,
                        desc=fac.get("desc", "") or fac.get("address", "")
                    )
                )
                if len(markers) >= 3:
                    break
            if markers:
                map_output = MapResponse(
                    link=f"https://map.kakao.com/link/to/{markers[0].name},{markers[0].lat},{markers[0].lng}",
                    data=MapData(
                        center=MapCenter(lat=markers[0].lat, lng=markers[0].lng),
                        markers=markers
                    ),
                    content="지도에서 위치를 확인해보세요!"
                )

        # 3) RAG 좌표로 못 만들었고 search_map_by_address 결과가 있으면 사용
        if map_output is None and map_response_from_tool:
            map_output = map_response_from_tool

        # 4) 최종 지도 응답 반환
        if map_output:
            logger.info("📍 지도 응답 반환")
            
            add_message(conversation_id, "ai", map_output)
            
            return ChatResponse(
                conversation_id=conversation_id,
                role="ai",
                type=map_output.type,
                content=map_output.content,
                link=map_output.link,
                data=map_output.data
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


@router.get("/chat/stream/{conversation_id}")
async def chat_status_stream(conversation_id: str):
    """
    SSE 기반 진행 상태 스트리밍 엔드포인트.
    tools에서 set_status가 호출되면 상태를 푸시합니다.
    """

    async def event_generator():
        last_status = None
        try:
            while True:
                status = get_status(conversation_id)
                if status and status != last_status:
                    payload = json.dumps(
                        {"conversation_id": conversation_id, "status": status},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
                    last_status = status
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return

    return StreamingResponse(event_generator(), media_type="text/event-stream")
