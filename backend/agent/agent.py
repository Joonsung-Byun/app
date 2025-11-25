from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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
from agent.callbacks import ToolTimingCallbackHandler


def create_agent():
    """LangChain Agent 생성"""
    llm = get_llm()

    # 모든 도구들을 하나의 리스트로 구성
    tools = [
        extract_user_intent,
        get_weather_forecast,
        search_facilities,
        show_map_for_facilities,
        naver_web_search,
        naver_cafe_search,
        create_search_map_tool(),  
    ]

    # 프롬프트 정의
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("system", "현재 대화 ID: {conversation_id}"),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Function Agent 생성
    agent = create_tool_calling_agent(llm, tools, prompt)

    # AgentExecutor 래핑
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        return_intermediate_steps=True,
        callbacks=[ToolTimingCallbackHandler()],
    )
