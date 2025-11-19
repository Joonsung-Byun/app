from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
import json

logger = logging.getLogger(__name__)

# 메모리에 대화 히스토리 저장
conversation_history: Dict[str, List] = {}

shown_facilities_history: Dict[str, set] = {}

# 마지막 검색 결과 저장 (conversation_id -> facilities)
last_search_results: Dict[str, List[Dict]] = {}

def get_conversation_history(conversation_id: str) -> List:
    """대화 히스토리 가져오기"""
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
        logger.info(f"새로운 대화 시작: {conversation_id}")
    else:
        logger.info(f"기존 대화 로드: {conversation_id} ({len(conversation_history[conversation_id])}개 메시지)")
    
    return conversation_history[conversation_id]

def add_message(conversation_id: str, role: str, content: str):
    """메시지 추가"""
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    if role == "user":
        conversation_history[conversation_id].append(HumanMessage(content=content))
    elif role == "ai":
        conversation_history[conversation_id].append(AIMessage(content=content))
    elif role == "search_result":
        conversation_history[conversation_id].append(SystemMessage(content=content))
    
    logger.info(f"메시지 추가: {conversation_id} - {role}: {content[:100]}...")

def save_search_results(conversation_id: str, facilities: List[Dict]):
    """검색 결과 저장"""
    last_search_results[conversation_id] = facilities
    
    # 시스템 메시지로도 저장 (Agent가 참조할 수 있게)
    facilities_summary = json.dumps(facilities, ensure_ascii=False)

    if conversation_id not in shown_facilities_history:
        shown_facilities_history[conversation_id] = set()
    
    for fac in facilities:
        # 메타데이터의 키가 'Name'인지 'name'인지 확인하여 저장
        name = fac.get("name") or fac.get("Name")
        if name:
            shown_facilities_history[conversation_id].add(name)

    print(f"저장된 시설 이름: {shown_facilities_history[conversation_id]}")
    

def get_shown_facility_names(conversation_id: str) -> List[str]:
    """지금까지 보여준 시설 이름 목록 반환 (필터링용)"""
    if conversation_id in shown_facilities_history:
        return list(shown_facilities_history[conversation_id])
    return []

def get_last_search_results(conversation_id: str) -> Optional[List[Dict]]:
    """마지막 검색 결과 가져오기"""
    return last_search_results.get(conversation_id)

def clear_conversation(conversation_id: str):
    """대화 히스토리 삭제"""
    if conversation_id in conversation_history:
        del conversation_history[conversation_id]
    if conversation_id in last_search_results:
        del last_search_results[conversation_id]
    logger.info(f"대화 삭제: {conversation_id}")

def get_all_conversations() -> Dict:
    """모든 대화 ID 목록"""
    return {
        conv_id: len(messages) 
        for conv_id, messages in conversation_history.items()
    }
