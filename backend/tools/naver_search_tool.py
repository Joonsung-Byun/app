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
from datetime import datetime, timedelta
from models.chat_models import get_llm
from utils.conversation_memory import save_search_results, get_shown_facility_names, set_status

FULL_MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"

# ============================================
# 1. 비동기 크롤링 헬퍼 함수
# ============================================
async def fetch_single_blog(session, link: str) -> str:
    """개별 네이버 블로그를 비동기로 크롤링."""
    try:
        target_link = link
        if "blog.naver.com" in link and "m.blog.naver.com" not in link:
            target_link = link.replace("blog.naver.com", "m.blog.naver.com")

        headers = {
            "User-Agent": FULL_MOBILE_USER_AGENT
        }
        async with session.get(target_link, headers=headers, timeout=3) as resp:
            if resp.status != 200: return ""
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            
            content = soup.find("div", class_="se-main-container")
            if not content:
                content = soup.find("div", id="postViewArea")

            if content:
                return content.get_text(" ", strip=True)[:850] 

            return ""

    except Exception as e:
        return ""

async def fetch_multiple_urls(links: List[str]) -> List[str]:
    """여러 블로그 링크를 동시에(병렬로) 크롤링."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_single_blog(session, link) for link in links]
        return await asyncio.gather(*tasks)

# ============================================
# 2. 날짜 계산 유틸리티 (기존과 동일)
# ============================================
WEEKDAY_MAP = {
    "월요일": 0, "월": 0, "화요일": 1, "화": 1, "수요일": 2, "수": 2,
    "목요일": 3, "목": 3, "금요일": 4, "금": 4, "토요일": 5, "토": 5, "일요일": 6, "일": 6
}

def calculate_date_range(keyword: str) -> str:
    today = datetime.now().date()
    if "오늘" in keyword: return f"기간: {today.strftime('%Y.%m.%d')}"
    elif "내일" in keyword: return f"기간: {(today + timedelta(days=1)).strftime('%Y.%m.%d')}"
    elif "이번 주말" in keyword or "주말" in keyword:
        current_weekday = today.weekday() 
        days_until_saturday = 5 - current_weekday
        if days_until_saturday < 0: days_until_saturday += 7 
        saturday = today + timedelta(days=days_until_saturday)
        sunday = saturday + timedelta(days=1)
        return f"기간: {saturday.strftime('%Y.%m.%d')} ~ {sunday.strftime('%Y.%m.%d')}"
    elif "다음 주" in keyword and "주말" not in keyword:
        days_until_next_monday = 7 - today.weekday()
        monday_next_week = today + timedelta(days=days_until_next_monday)
        sunday_next_week = monday_next_week + timedelta(days=6)
        return f"기간: {monday_next_week.strftime('%Y.%m.%d')} ~ {sunday_next_week.strftime('%Y.%m.%d')}"
    elif "다음 주말" in keyword:
        days_until_next_monday = 7 - today.weekday()
        monday_next_week = today + timedelta(days=days_until_next_monday)
        return f"기간: {(monday_next_week + timedelta(days=5)).strftime('%Y.%m.%d')} ~ {(monday_next_week + timedelta(days=6)).strftime('%Y.%m.%d')}"
    if "이번 주" in keyword:
        for day_name, day_index in WEEKDAY_MAP.items():
            if f"이번 주 {day_name}" in keyword or f"이번 주 {day_name[:-2]}" in keyword:
                days_diff = day_index - today.weekday()
                if days_diff < 0: days_diff += 7
                return f"기간: {(today + timedelta(days=days_diff)).strftime('%Y.%m.%d')}"
    return ""

# ============================================
# 3. AI 분석 데이터 모델 
# ============================================
class SearchResultItem(BaseModel):
    title: str = Field(description="블로그 제목")
    link: str = Field(description="블로그 링크")
    description: str = Field(description="요약 내용")
    venue: str = Field(description="정확한 장소명(없으면 빈칸)")

class SearchAnalysisResult(BaseModel):
    results: List[SearchResultItem]

# ============================================
# 4. 툴 정의 
# ============================================
@tool
async def naver_web_search(query: str, conversation_id: str) -> str:
    """
    네이버 블로그 검색 -> 상위 결과 병렬 크롤링 -> 정확한 장소명 추출의 과정을 거칩니다. (완전 비동기)
    """
    naver_client_id = settings.NAVER_CLIENT_ID
    naver_client_secret = settings.NAVER_CLIENT_SECRET
    
    if not naver_client_id or not naver_client_secret:
        return "오류: config에 네이버 API 키가 설정되지 않았습니다."

    # [Step 1] 날짜 계산 & 쿼리 생성
    date_info = calculate_date_range(query)
    final_query = f"{query} {date_info}" if date_info else query
    
    today = datetime.now()
    if str(today.year) not in final_query and not date_info:
         final_query = f"{today.year}년 {today.month}월 {final_query}"

    shown_items = set(get_shown_facility_names(conversation_id)) if conversation_id else set()

    # [Step 2] 네이버 API 호출 
    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {"X-Naver-Client-Id": naver_client_id, "X-Naver-Client-Secret": naver_client_secret}
    params = {"query": final_query, "display": 10, "sort": "sim"}

    try:
        if conversation_id:
            set_status(conversation_id, "웹 정보 확인 중..")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return f"네이버 API 오류 발생 (상태코드: {resp.status})"
                data = await resp.json() 
        
        if not data.get('items'): return f"'{final_query}' 검색 결과가 없습니다."

        raw_items = []
        for item in data['items']:
            title = item['title'].replace("<b>", "").replace("</b>", "")
            link = item['link']
            if title in shown_items: continue
            
            raw_items.append({
                "title": title,
                "link": link,
                "description": item['description'].replace("<b>", "").replace("</b>", ""),
                "postdate": item.get('postdate', '')
            })

        if not raw_items: return "새로운 검색 결과가 없습니다."

        # [Step 3] 1차 필터링
        llm = get_llm()
        parser = JsonOutputParser(pydantic_object=SearchAnalysisResult)
        
        prompt_filter = PromptTemplate(
            template="""
사용자 질문: "{user_query}" (날짜힌트: {date_info})
오늘 날짜: {today_date}

아래 블로그 목록 중 가장 관련성 높고 최신 정보인 **상위 3개**만 선택하세요.
(작년 글, 광고, 관련 없는 지역 제외)
추론 및 thinking은 하지 말고 출력 형식에 따라 답변만 작성하세요.

목록:
{raw_data}

출력 형식: JSON
{format_instructions}
""",
            input_variables=["user_query", "date_info", "today_date", "raw_data"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        raw_text_list = [f"- 제목: {i['title']}\n  링크: {i['link']}\n  요약: {i['description']}\n  날짜: {i['postdate']}" for i in raw_items[:10]]
        
        chain = prompt_filter | llm | parser
        analysis = await chain.ainvoke({
            "user_query": query,
            "date_info": date_info,
            "today_date": today.strftime("%Y-%m-%d"),
            "raw_data": "\n\n".join(raw_text_list)
        })
        
        top_3_results = analysis['results']

       # [Step 4] 2차 정밀 분석 
        target_links = [item['link'] for item in top_3_results]
        
        # 3. 비동기 크롤링 실행 
        crawled_contents = await fetch_multiple_urls(target_links)

        final_output_results = []
        
        for idx, item in enumerate(top_3_results):
            full_text = crawled_contents[idx]
            
            if full_text:
                # 4. LLM에게 분석 요청 
                refine_prompt = f"""
                블로그 본문을 읽고 다음 두 가지 정보를 JSON 형식으로 추출해.
                
                [본문]: {full_text[:850]}...
                
                [미션]
                1. venue: 행사가 열리는 **검색 가능한 건물명/시설명**만 추출해. 
                   - [중요] 'OOO센터 3층', 'OO홀' 처럼 층수나 호수는 제발 빼줘. (지도 검색에 방해됨)
                   - 예: "벡스코 제1전시장 2홀" (X) -> "벡스코 제1전시장" (O)
                   - 장소가 없으면 '장소 불명'이라고 적어.

                2. summary: 행사의 핵심 정보(일정, 시간, 입장료, 꿀팁 등)를 1~2문장으로 요약해.
                
                [출력 예시]
                {{
                    "venue": "성수동 에스팩토리 D동",
                    "summary": "11월 25일까지 진행되며 입장료는 무료입니다. 대기 시간이 기니 오픈런을 추천합니다."
                }}
                """
                
                try:
                    refined_result_msg = await llm.ainvoke(refine_prompt)
                    refined_result = refined_result_msg.content.strip()
                    
                    refined_result = refined_result.replace("```json", "").replace("```", "")
                    refined_data = json.loads(refined_result)
                    
                    if refined_data.get("venue") and "불명" not in refined_data["venue"]:
                        item['venue'] = refined_data["venue"]
                    
                    if refined_data.get("summary"):
                        item['description'] = "✨AI요약: " + refined_data["summary"]
                        
                except Exception as e:
                    pass
            
            final_output_results.append(item)

        # [Step 5] 결과 반환
        if conversation_id:
            save_data = [
                {
                    "name": item.get("venue") or item.get("title"),
                    "link": item.get("link"),
                    "desc": item.get("description", "")
                }
                for item in final_output_results
            ]
            save_search_results(conversation_id, save_data)

        result_text = f"🔍 '{final_query}' 검색 및 정밀 분석 결과:\n\n"
        
        for idx, item in enumerate(final_output_results, 1):
            html_link = f'<a href="{item["link"]}" target="_blank">👉 블로그 보기</a>'
            result_text += f"{idx}. **{item['title']}**\n"
            result_text += f"   - 📍 장소: {item['venue']}\n" 
            result_text += f"   - 📝 내용: {item['description']}\n"
            result_text += f"   - {html_link}\n\n"
            
        return result_text

    except Exception as e:
        return f"검색 분석 중 오류 발생: {str(e)}"
