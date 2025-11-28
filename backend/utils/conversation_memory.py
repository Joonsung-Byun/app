from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
import json
from models.map_models import MapResponse

logger = logging.getLogger(__name__)

# 메모리에 대화 히스토리 저장
conversation_history: Dict[str, List] = {}

shown_facilities_history: Dict[str, set] = {}

# 마지막 검색 결과 저장 (conversation_id -> facilities)
last_search_results: Dict[str, List[Dict]] = {}

# 마지막 검색 결과의 출처 저장 (conversation_id -> "rag" / "web" / "cafe")
last_result_source: Dict[str, str] = {}

# 진행 상태 저장 (conversation_id -> status text)
current_status: Dict[str, str] = {}

def get_conversation_history(conversation_id: str) -> List:
    """대화 히스토리 가져오기"""
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
        logger.info(f"새로운 대화 시작: {conversation_id}")
    else:
        logger.info(f"기존 대화 로드: {conversation_id} ({len(conversation_history[conversation_id])}개 메시지)")
    
    return conversation_history[conversation_id]

def add_message(conversation_id: str, role: str, content):
    """메시지 추가 (MapResponse 같은 객체도 안전하게 처리)"""
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []

    # 🔹 MapResponse처럼 객체가 들어온 경우 → 히스토리에는 문자열로만 저장
    if isinstance(content, MapResponse):
        try:
            marker_name = (
                content.data.markers[0].name
                if content.data and content.data.markers
                else "지도 응답"
            )
            safe_content = f"[지도 응답] {marker_name}"
        except Exception:
            safe_content = "[지도 응답]"
    else:
        # 나머지는 전부 문자열로 캐스팅 (dict, list, 기타 객체 포함)
        if not isinstance(content, str):
            safe_content = str(content)
        else:
            safe_content = content

    if role == "user":
        conversation_history[conversation_id].append(
            HumanMessage(content=safe_content)
        )
    elif role == "ai":
        conversation_history[conversation_id].append(
            AIMessage(content=safe_content)
        )
    elif role == "search_result":
        conversation_history[conversation_id].append(
            SystemMessage(content=safe_content)
        )

    logger.info(
        f"메시지 추가: {conversation_id} - {role}: {safe_content[:100]}..."
    )

def save_search_results(conversation_id: str, facilities: List[Dict], source: str = "rag"):
    """검색 결과를 메모리에 저장 (지도 표시 및 중복 방지용)

    source: "rag" / "web" / "cafe" 등 검색 출처 태그
    """
    
    if not facilities:
        logger.info(f"⚠️ 검색 결과 없음(0건) -> 메모리 저장 건너뜀: {conversation_id}")
        return

    # 1. 마지막 검색 결과 갱신 (지도 툴용)
    last_search_results[conversation_id] = facilities
    last_result_source[conversation_id] = source

    # 디버깅용 출력 (최소 정보만)
    try:
        print(f"[MEMORY] save_search_results: conv={conversation_id}, source={source}, count={len(facilities)}")
    except Exception:
        pass
    
    # 2. 중복 방지 히스토리 누적 (추천 제외용)
    if conversation_id not in shown_facilities_history:
        shown_facilities_history[conversation_id] = set()
    
    for fac in facilities:
        # 메타데이터의 키가 RAG는 'Name', Web은 'title'일 수 있으므로 안전하게 가져옴
        name = fac.get("name") or fac.get("Name") or fac.get("title")
        if name:
            shown_facilities_history[conversation_id].add(name)
            
    logger.info(f"✅ 검색 결과 메모리 저장 완료: {len(facilities)}개 (source={source})")

    

def get_shown_facility_names(conversation_id: str) -> List[str]:
    """지금까지 보여준 시설 이름 목록 반환 (필터링용)"""
    if conversation_id in shown_facilities_history:
        return list(shown_facilities_history[conversation_id])
    return []

def get_last_search_results(conversation_id: str) -> Optional[List[Dict]]:
    """마지막 검색 결과 가져오기"""
    return last_search_results.get(conversation_id)

def get_last_result_source(conversation_id: str) -> str:
    """마지막 검색 결과의 출처 반환 ('rag' / 'web' / 'cafe' / '')"""
    return last_result_source.get(conversation_id, "")

def clear_conversation(conversation_id: str):
    """대화 히스토리 삭제"""
    if conversation_id in conversation_history:
        del conversation_history[conversation_id]
    if conversation_id in last_search_results:
        del last_search_results[conversation_id]
    if conversation_id in last_result_source:
        del last_result_source[conversation_id]
    logger.info(f"대화 삭제: {conversation_id}")

def get_all_conversations() -> Dict:
    """모든 대화 ID 목록"""
    return {
        conv_id: len(messages) 
        for conv_id, messages in conversation_history.items()
    }

def set_status(conversation_id: str, status: str):
    """현재 진행 상태를 저장 (예: 의도 파악 중, 시설 검색 중 등)"""
    current_status[conversation_id] = status
    logger.info(f"[STATUS] {conversation_id}: {status}")

def get_status(conversation_id: str) -> str:
    """저장된 진행 상태를 반환 (없으면 빈 문자열)"""
    return current_status.get(conversation_id, "")
