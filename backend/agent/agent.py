from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
try:
    from agent.callbacks import ToolTimingCallbackHandler
    callbacks = [ToolTimingCallbackHandler()]
except ImportError:
    callbacks = []

from models.chat_models import get_llm
from tools import (
    extract_user_intent,    
    get_weather_forecast,   
    search_facilities,      
    show_map_for_facilities, 
    naver_web_search,     
    naver_cafe_search,       
    create_search_map_tool,   
)
from agent.prompts import SYSTEM_PROMPT


def create_agent():
    """LangChain Agent 생성"""
    llm = get_llm()

    # 1. 모든 도구 등록
    tools = [
        extract_user_intent,
        get_weather_forecast,
        search_facilities,        
        show_map_for_facilities,
        naver_web_search,         
        naver_cafe_search,        
        create_search_map_tool(),
    ]

    # 2. 프롬프트 정의
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("system", "현재 대화 ID: {conversation_id}"), 
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 3. Agent 생성 (Function Calling 방식)
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 4. AgentExecutor 생성
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,            
        max_iterations=5,             
        return_intermediate_steps=True, 
        handle_parsing_errors=True,  
        callbacks=callbacks,          
    )