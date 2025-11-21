from langchain.tools import StructuredTool
from models.map_models import MapResponse
from tools.geocoding_tool import search_map_by_address_core 


def create_search_map_tool():
    """
    search_map_by_address_core() → StructuredTool 로 감싸서 반환
    LangChain이 Pydantic 객체를 그대로 반환하도록 함.
    """
    
    # func는 반드시 파라미터 하나만 받는 형태여야 함
    # StructuredTool은 Pydantic 객체를 바로 반환하도록 허용됨.
    return StructuredTool.from_function(
        name="search_map_by_address",
        description="주소/장소명으로 지도 데이터를 생성하는 툴",
        func=search_map_by_address_core,
        return_direct=True  
    )