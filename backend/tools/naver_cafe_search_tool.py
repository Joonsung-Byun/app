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
from utils.conversation_memory import save_search_results, get_shown_facility_names, set_status 

# 맘카페 차단 회피를 위한 완전한 User-Agent
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"

# ============================================
# 1. 비동기 크롤링 헬퍼 함수
# ============================================

async def fetch_single_cafe(session, link: str) -> str:
    """개별 카페 글을 비동기로 크롤링."""
    try:
        # 모바일 링크로 변환하여 본문 접근 용이하게 함
        target = link.replace("cafe.naver.com", "m.cafe.naver.com")
        headers = {"User-Agent": USER_AGENT} 
        
        async with session.get(target, headers=headers, timeout=3) as resp:
            if resp.status != 200: return ""
            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
        
            # 본문 내용 추출
            content = soup.find("div", class_="se-main-container")
            if not content: content = soup.find("div", id="postContent")
            
            if content: return content.get_text(" ", strip=True)[:850]
            return ""
    except:
        return ""

async def fetch_cafe_urls(links: List[str]):
    """여러 카페 글을 병렬로 크롤링."""
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[fetch_single_cafe(session, l) for l in links])

# ============================================
# 2. AI 분석 데이터 모델
# ============================================

class CafeItem(BaseModel):
    title: str = Field(description="제목")
    link: str = Field(description="링크")
    summary: str = Field(description="솔직 요약")
    sentiment: str = Field(description="긍정/부정/중립")

class CafeAnalysis(BaseModel):
    results: List[CafeItem]

# ============================================
# 3. 툴 정의 
# ============================================

@tool
async def naver_cafe_search(query: str, conversation_id: str) -> str:
    """
    네이버 맘카페를 검색하여 '솔직 후기', '장단점', '주차/웨이팅 꿀팁'을 확인합니다. (완전 비동기)
    검증이나 평판 조회가 필요할 때 사용하세요.
    """
    naver_id = settings.NAVER_CLIENT_ID
    naver_secret = settings.NAVER_CLIENT_SECRET
    
    if not naver_id or not naver_secret:
        return "오류: 서버 설정(config)에 네이버 API 키가 누락되었습니다."

    # [Step 1] 카페 검색 API 설정
    url = "https://openapi.naver.com/v1/search/cafearticle.json"
    headers = {
        "X-Naver-Client-Id": naver_id, 
        "X-Naver-Client-Secret": naver_secret
    }
    params = {"query": query, "display": 10, "sort": "sim"} 
    
    try:
        if conversation_id:
            set_status(conversation_id, "맘카페 후기 검색 중...")
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
        
                # API 호출 실패 오류 방지 (resp.status 사용)
                if resp.status != 200:
                    return f"네이버 API 오류 발생 (상태코드: {resp.status})"

                # 응답 JSON을 비동기로 가져오기
                data = await resp.json() 
        
        if not data.get('items'): return "관련 카페 후기가 없습니다."

        raw_items = []
        shown = set(get_shown_facility_names(conversation_id)) if conversation_id else set()
        
        for item in data['items']:
            title = item['title'].replace("<b>","").replace("</b>","")
            if title in shown: continue
            raw_items.append({"title": title, "link": item['link'], "desc": item['description']})

        if not raw_items: return "새로운 후기가 없습니다."

        # [Step 2] LLM 1차 선별 (
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
        
        chain = prompt | llm | parser
        analysis = await chain.ainvoke({"user_query": query, "raw_data": raw_text})
        top_3 = analysis['results']

        # [Step 3] 비동기 병렬 크롤링 (await 사용)
        target_links = [item['link'] for item in top_3]
        contents = await fetch_cafe_urls(target_links) 

        final_results = []
        for idx, item in enumerate(top_3):
            full_text = contents[idx]
            
            if full_text:
                refine_prompt = f"""
                맘카페 후기 본문을 보고 '엄마들을 위한 찐 꿀팁'을 한 줄로 요약해줘.
                (예: 주차장 만차 시간, 준비물, 비추천 이유 등)
                
                [본문]: {full_text}
                """
                try:
                    tip_msg = await llm.ainvoke(refine_prompt)
                    tip = tip_msg.content.strip()
                    item['summary'] = f"{item['summary']} (💡 {tip})"
                except: pass
            
            final_results.append(item)

        # [Step 4] 반환
        if conversation_id:
            save_data = [
                {
                    "name": i.get("venue") or i.get("title"),
                    "link": i.get("link"),
                    "desc": i.get("summary", "")
                }
                for i in final_results
            ]
            save_search_results(conversation_id, save_data)

        res_text = f"☕ **'{query}' 맘카페 찐후기**\n"
        for i, item in enumerate(final_results, 1):
            icon = "👍" if item['sentiment'] == "긍정" else "💬"
            link = f'<a href="{item["link"]}" target="_blank">글 보기</a>'
            res_text += f"\n{i}. {icon} **{item['title']}**\n"
            res_text += f"   📝 {item['summary']}\n"
            res_text += f"   🔗 {link}\n"
            
        return res_text

    except Exception as e:
        return f"카페 검색 오류: {e}"
