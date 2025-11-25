from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from .geocoding_tool import search_map_by_address_core

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