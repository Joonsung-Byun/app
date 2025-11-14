from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from models.chat_models import get_llm
from tools import (
    extract_user_intent,
    get_weather_forecast,
    search_facilities,
    generate_kakao_map_link
)
from agent.prompts import SYSTEM_PROMPT

def create_agent():
    """LangChain Agent 생성"""
    llm = get_llm()
    
    tools = [
        extract_user_intent,
        get_weather_forecast,
        search_facilities,
        generate_kakao_map_link
    ]
    
    # chat_history placeholder 추가
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),  # 대화 히스토리
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        return_intermediate_steps=True
    )