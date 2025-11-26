from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from models.map_models import MapData, MapMarker, MapCenter 

class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")
    conversation_id: Optional[str] = Field(None, description="대화 ID (없으면 서버가 생성)")
    child_age: Optional[int] = Field(None, description="아이 나이 (선택)")

class ChatResponse(BaseModel):
    role: str = Field(..., description="메시지 역할 (user/ai)")
    content: str = Field(..., description="메시지 내용")
    type: str = Field(default="text", description="응답 타입 (text/map)")
    link: Optional[str] = Field(None, description="카카오맵 링크")
    data: Optional[MapData] = Field(None, description="지도 데이터")
    
    conversation_id: str = Field(..., description="대화 ID")


class ChatStatusResponse(BaseModel):
    conversation_id: str = Field(..., description="대화 ID")
    status: str = Field(default="", description="진행 상태 텍스트 (없으면 빈 문자열)")
