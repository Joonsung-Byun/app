import requests
import json
from langchain.tools import tool
from config import settings

from utils.conversation_memory import get_shown_facility_names, save_search_results

@tool
def naver_web_search(
    query: str, 
    conversation_id: str  # 🟢 필수 파라미터 추가
) -> str:
    """
    네이버 검색 API(블로그)를 사용하여 최신 정보, 축제, 행사, 후기를 검색합니다.
    반드시 conversation_id를 함께 전달해야 중복된 결과를 방지할 수 있습니다.
    """
    
    naver_client_id = settings.NAVER_CLIENT_ID
    naver_client_secret = settings.NAVER_CLIENT_SECRET
    
    if not naver_client_id or not naver_client_secret:
        return "오류: config에 네이버 API 키가 설정되지 않았습니다."

    # 1. 이미 보여준 항목들(중복 필터용) 가져오기
    # 네이버 검색의 경우 '블로그 제목'이나 '링크'를 식별자로 사용합니다.
    shown_items = set(get_shown_facility_names(conversation_id)) if conversation_id else set()
    
    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    # 중복을 거르고도 충분한 개수를 확보하기 위해 넉넉하게 요청 (예: 10개)
    params = {
        "query": query,
        "display": 10, 
        "sort": "sim" 
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return f"네이버 검색 에러: {response.status_code}"
            
        data = response.json()
        if not data.get('items'):
            return "검색 결과가 없습니다."

        filtered_items = []
        for item in data['items']:
            # HTML 태그 제거 및 정리
            title = item['title'].replace("<b>", "").replace("</b>", "")
            desc = item['description'].replace("<b>", "").replace("</b>", "")
            link = item['link']
            
            # 🔴 중복 검사: 제목이 이미 기억 속에 있다면 건너뜀
            if title in shown_items:
                continue
                
            filtered_items.append({
                "name": title,  # 메모리 저장을 위해 'name' 키 사용
                "description": desc,
                "link": link
            })
            
            # 3개만 확보되면 중단 (너무 많이 보여주면 토큰 낭비)
            if len(filtered_items) >= 3:
                break
        
        if not filtered_items:
            return "새로운 검색 결과가 없습니다. (이전과 동일한 결과 제외됨)"

        # 2. 이번에 찾은 결과를 메모리에 저장 (다음 턴 중복 방지)
        if conversation_id:
            save_search_results(conversation_id, filtered_items)

        # LLM에게 보여줄 텍스트 생성
        result_text = f"🔍 '{query}' 네이버 블로그 검색 결과 (중복 제외됨):\n"
        for idx, item in enumerate(filtered_items, 1):
            result_text += f"[{idx}] {item['name']}\n   - 요약: {item['description']}\n   - 링크: {item['link']}\n"
            
        return result_text

    except Exception as e:        return f"검색 예외 발생: {str(e)}"