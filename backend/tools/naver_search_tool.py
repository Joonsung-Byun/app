import os
import requests
import json
from langchain.tools import tool      
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

@tool
def naver_web_search(query: str) -> str:
    """
    네이버 검색 API(블로그)를 사용하여 최신 정보, 축제, 행사, 후기를 검색합니다.
    RAG 검색 결과가 없거나, '축제', '이번주', '후기' 등의 키워드가 있을 때 사용하세요.
    """
    # 1. URL 설정 블로그 검색으로 후기/장소 찾기
    url = "https://openapi.naver.com/v1/search/blog.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    # 2. 정확도순(sim)으로 상위 5개만 가져옴
    params = {
        "query": query,
        "display": 5,
        "sort": "sim" 
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return f"네이버 검색 에러: {response.status_code}"
            
        data = response.json()
        
        if not data.get('items'):
            return "네이버 검색 결과가 없습니다."

        # 3. 결과 텍스트 포맷팅
        result_text = f"🔍 '{query}' 네이버 블로그 검색 결과:\n"
        for idx, item in enumerate(data['items'], 1):
            # HTML 태그 제거
            title = item['title'].replace("<b>", "").replace("</b>", "")
            desc = item['description'].replace("<b>", "").replace("</b>", "")
            link = item['link']
            
            result_text += f"{idx}. {title}\n   - 내용: {desc}\n   - 링크: {link}\n"
            
        return result_text

    except Exception as e:
        return f"검색 예외 발생: {str(e)}"

# 👇 테스트용
if __name__ == "__main__":
    print("🚀 테스트 시작합니다...")  # 이게 출력되는지 봐줘
    result = naver_web_search.invoke("서울 아이랑 갈만한 곳")
    print(result)
    print("🏁 테스트 끝!")
