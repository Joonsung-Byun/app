from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
import json

logger = logging.getLogger(__name__)

# 메모리에 대화 히스토리 저장
conversation_history: Dict[str, List] = {}

# 마지막 검색 결과 저장 (conversation_id -> facilities)
last_search_results: Dict[str, List[Dict]] = {}

# 현재 실행 중인 conversation_id 저장 (추가!)
_current_conversation_id: Optional[str] = None

def set_current_conversation_id(conversation_id: str):
    """현재 실행 중인 conversation_id 설정"""
    global _current_conversation_id
    _current_conversation_id = conversation_id
    logger.info(f"현재 conversation_id 설정: {conversation_id}")

def get_current_conversation_id() -> Optional[str]:
    """현재 실행 중인 conversation_id 가져오기"""
    return _current_conversation_id

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
    
    
    logger.info(f"검색 결과 저장: {conversation_id} - {len(facilities)}개 시설")

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