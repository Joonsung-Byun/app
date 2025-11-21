from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from models.chat_models import get_llm
from tools import (
    extract_user_intent,
    get_weather_forecast,
    search_facilities,
    #generate_kakao_map_link,
    show_map_for_facilities,
    naver_web_search,
    search_map_by_address
)
from agent.prompts import SYSTEM_PROMPT

def create_agent():
    """LangChain Agent 생성"""
    llm = get_llm()
    
    tools = [
        extract_user_intent,
        get_weather_forecast,
        search_facilities,
        #generate_kakao_map_link,
        show_map_for_facilities,
        naver_web_search,
        search_map_by_address
    ]
    
    # chat_history placeholder 추가
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("system", "현재 대화 ID: {conversation_id}"),
        MessagesPlaceholder(variable_name="chat_history", optional=True),  # 대화 히스토리
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        return_intermediate_steps=True
    )
