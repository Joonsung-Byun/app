from langchain.tools import tool
import requests
from config import settings  # 수정
from datetime import datetime, timedelta
import json
from utils.conversation_memory import set_status

def get_target_datetime(date_str: str) -> datetime:
    """날짜 문자열을 datetime으로 변환"""
    today = datetime.now()
    
    if date_str == "today":
        return today
    elif date_str == "tomorrow":
        return today + timedelta(days=1)
    elif date_str == "this_weekend":
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0 and today.hour >= 12:
            days_until_saturday = 7
        return today + timedelta(days=days_until_saturday)
    else:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return today

@tool
def get_weather_forecast(city_name: str, date: str = "today", conversation_id: str = "") -> str:
    """
    특정 날짜의 날씨 예보를 조회합니다.
    
    Args:
        city_name: 도시 이름
        date: 날짜
    
    Returns:
        날씨 정보 JSON
    """
    if conversation_id:
        set_status(conversation_id, f"{city_name}의 날씨 정보 확인 중..")

    city_mapping = {
        "서울": "Seoul",
        "부산": "Busan",
        "대구": "Daegu",
        "인천": "Incheon",
        "광주": "Gwangju",
        "대전": "Daejeon",
        "울산": "Ulsan",
        "경기": "Gyeonggi",
        "수원": "Suwon",
        "순천": "Suncheon",
        "제주": "Jeju",
        "강릉": "Gangneung",
        "전주": "Jeonju",
        "창원": "Changwon",
        "포항": "Pohang",
        "여수": "Yeosu",
        "천안": "Cheonan",
        "안동": "Andong",
        "김해": "Gimhae",

        "청주": "Cheongju",
        "충주": "Chungju",

        "경주": "Gyeongju",
        "양산": "Yangsan",
        "진주": "Jinju",
        "구미": "Gumi",
        "목포": "Mokpo",
        "군산": "Gunsan",
        "익산": "Iksan",
        "광양": "Gwangyang",
        "김포": "Gimpo",
        "오산": "Osan",
        "의정부": "Uijeongbu",
        "평택": "Pyeongtaek",
        "포천": "Pocheon",
        "이천": "Icheon",
        "여주": "Yeoju",

        "양평": "Yangpyeong",
        "홍천": "Hongcheon",
        "횡성": "Hoengseong",
        "태백": "Taebaek",
        "속초": "Sokcho",
        "동해": "Donghae",
        "삼척": "Samcheok",
        "정선": "Jeongseon",
        "고성": "Goseong",
        "인제": "Inje",
        "철원": "Cheorwon",

        "화천": "Hwacheon",
        "양구": "Yanggu",
        "춘천": "Chuncheon",

        "원주": "Wonju",
        "강화": "Ganghwa",

        "남양주": "Namyangju",
        "파주": "Paju",
        
    }
    
    english_city = city_mapping.get(city_name, city_name)
    
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": f"{english_city},KR",
        "appid": settings.OPENWEATHER_API_KEY,
        "lang": "kr",
        "units": "metric"
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return json.dumps({
            "success": False,
            "message": f"날씨 정보를 가져올 수 없습니다: {city_name}"
        }, ensure_ascii=False)
    
    data = response.json()
    forecast_list = data["list"]
    
    target_datetime = get_target_datetime(date)
    target_date_str = target_datetime.strftime("%Y-%m-%d")
    
    target_forecast = None
    for forecast in forecast_list:
        dt_txt = forecast["dt_txt"]
        if target_date_str in dt_txt:
            target_forecast = forecast
            break
    
    if not target_forecast:
        target_forecast = forecast_list[0]
    
    weather_main = target_forecast["weather"][0]["main"].lower()
    description = target_forecast["weather"][0]["description"]
    temp = target_forecast["main"]["temp"]
    
    is_rainy = weather_main in ["rain", "drizzle", "thunderstorm"]
    is_snowy = weather_main in ["snow"]
    is_clear = weather_main in ["clear"]
    
    condition = "실내" if (is_rainy or is_snowy) else "실외"
    
    return json.dumps({
        "success": True,
        "city": city_name,
        "date": target_date_str,
        "weather": description,
        "temp": temp,
        "is_indoor": condition == "실내",
        "condition": condition
    }, ensure_ascii=False)
