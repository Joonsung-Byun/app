import requests
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List
from config import settings
from models.chat_models import get_llm
from utils.conversation_memory import save_search_results, get_shown_facility_names
import nest_asyncio

nest_asyncio.apply()

# --- 비동기 크롤링 함수 (블로그와 동일하게 재사용 가능하나, 카페 특화 처리 위해 별도 작성) ---
async def fetch_single_cafe(session, link: str) -> str:
    try:
        # 카페는 모바일 링크 변환이 더 중요함
        target = link.replace("cafe.naver.com", "m.cafe.naver.com")
        headers = {"User-Agent": "Mozilla/5.0 ..."} # (User-Agent 필수)
        
        async with session.get(target, headers=headers, timeout=3) as resp:
            if resp.status != 200: return ""
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 카페 본문 클래스 (se-main-container 등)
            content = soup.find("div", class_="se-main-container")
            if not content: content = soup.find("div", id="postContent")
            
            if content: return content.get_text(" ", strip=True)[:1500]
            return ""
    except:
        return ""

async def fetch_cafe_urls(links: List[str]):
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[fetch_single_cafe(session, l) for l in links])

# --- 데이터 모델 ---
class CafeItem(BaseModel):
    title: str = Field(description="제목")
    link: str = Field(description="링크")
    summary: str = Field(description="솔직 요약")
    sentiment: str = Field(description="긍정/부정/중립")

class CafeAnalysis(BaseModel):
    results: List[CafeItem]

@tool
def naver_cafe_search(query: str, conversation_id: str) -> str:
    """
    네이버 맘카페를 검색하여 '솔직 후기', '장단점', '주차/웨이팅 꿀팁'을 확인합니다.
    검증이나 평판 조회가 필요할 때 사용하세요.
    """
    naver_id = settings.NAVER_CLIENT_ID
    naver_secret = settings.NAVER_CLIENT_SECRET
    
    # [Step 1] 카페 검색 API
    url = "https://openapi.naver.com/v1/search/cafearticle.json"
    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
    params = {"query": query, "display": 15, "sort": "sim"} # 정확도순
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        if not data.get('items'): return "관련 카페 후기가 없습니다."

        raw_items = []
        shown = set(get_shown_facility_names(conversation_id)) if conversation_id else set()
        
        for item in data['items']:
            title = item['title'].replace("<b>","").replace("</b>","")
            if title in shown: continue
            raw_items.append({"title": title, "link": item['link'], "desc": item['description']})

        if not raw_items: return "새로운 후기가 없습니다."

        # [Step 2] LLM 1차 선별
        llm = get_llm()
        parser = JsonOutputParser(pydantic_object=CafeAnalysis)
        
        prompt = PromptTemplate(
            template="""
            사용자 질문: {user_query}
            아래 맘카페 글 중 **가장 솔직하고 도움되는 후기 3개**를 골라주세요.
            (단순 홍보, 질문글 제외. '다녀왔어요' 후기 우선)
            
            목록:
            {raw_data}
            
            출력 형식: JSON
            {format_instructions}
            """,
            input_variables=["user_query", "raw_data"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        raw_text = "\n".join([f"- {i['title']} ({i['link']}) : {i['desc']}" for i in raw_items[:10]])
        analysis = (prompt | llm | parser).invoke({"user_query": query, "raw_data": raw_text})
        top_3 = analysis['results']

        # [Step 3] ⚡ 카페글 비동기 병렬 크롤링
        target_links = [item['link'] for item in top_3]
        contents = asyncio.run(fetch_cafe_urls(target_links))

        final_results = []
        for idx, item in enumerate(top_3):
            full_text = contents[idx]
            
            # 본문을 긁어왔으면 내용을 더 보강함 (안 긁혔으면 1차 LLM 결과 그대로 사용)
            if full_text:
                refine_prompt = f"""
                맘카페 후기 본문을 보고 '엄마들을 위한 찐 꿀팁'을 한 줄로 요약해줘.
                (예: 주차장 만차 시간, 준비물, 비추천 이유 등)
                
                [본문]: {full_text}
                """
                try:
                    tip = llm.invoke(refine_prompt).content.strip()
                    item['summary'] = f"{item['summary']} (💡 {tip})"
                except: pass
            
            final_results.append(item)

        # [Step 4] 반환
        if conversation_id:
             save_data = [{"name": i['title'], "link": i['link']} for i in final_results]
             save_search_results(conversation_id, save_data)

        res_text = f"☕ **'{query}' 맘카페 찐후기**:\n\n"
        for i, item in enumerate(final_results, 1):
            icon = "👍" if item['sentiment'] == "긍정" else "💬"
            link = f'<a href="{item["link"]}" target="_blank">글 보기</a>'
            res_text += f"{i}. {icon} **{item['title']}**\n   🗣️ {item['summary']}\n   🔗 {link}\n\n"
            
        return res_text

    except Exception as e:
        return f"카페 검색 오류: {e}"