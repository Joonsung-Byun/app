from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from .geocoding_tool import search_map_by_address_core
from utils.conversation_memory import get_last_result_source
import json
# 1. 툴의 입력 스키마 정의 (LLM에게 노출되는 파라미터)
class SearchMapInput(BaseModel):
    place_name_or_address: str = Field(
        description="검색할 장소 이름 또는 정확한 주소. 예: '서울시청', '판교역'."
    )
    conversation_id: str = Field(
        description="현재 대화 ID (시스템 규칙 준수를 위해 받지만, 실제 사용되지 않음).",
        default=""
    )

# 2. 래퍼 함수 정의
def _map_tool_wrapper(place_name_or_address: str, conversation_id: str = "") -> str:
    """
    LLM의 호출 규칙을 맞추기 위한 래퍼 함수. 
    conversation_id를 받지만, 실제 코어 함수에는 전달하지 않습니다.
    """
    # ✅ 강제 규칙: 직전 출처가 RAG면 이 도구 금지
    if conversation_id:
        last_source = get_last_result_source(conversation_id)
        if last_source == "rag":
            print("[MAP TOOL] 최근 검색 출처가 'rag'이므로 search_map_by_address 도구 사용 금지")
            return json.dumps({
                "success": False,
                "message": "[SYSTEM] 최근 검색 출처가 'rag'입니다. "
                           "이 경우에는 search_map_by_address가 아니라 "
                           "show_map_for_facilities 도구를 사용해야 합니다."
            }, ensure_ascii=False)

    # 그 외에는 원래대로 주소/장소명 지오코딩
    return search_map_by_address_core(place_name_or_address)


# 3. StructuredTool 생성 함수 (Factory)
def create_search_map_tool() -> StructuredTool:
    """
    StructuredTool을 생성하여 반환하는 Factory 함수
    """
    return StructuredTool.from_function(
        func=_map_tool_wrapper,  
        name="search_map_by_address",
        description="특정 장소 이름이나 주소를 검색하여 지도 좌표를 반환하는 도구입니다. 대화 기록이 아닌, 입력된 장소나 주소에만 사용하세요.",
        args_schema=SearchMapInput,  
    )