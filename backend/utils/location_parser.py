def parse_location(user_message: str) -> str | None:
    """
    사용자 메시지에서 지역명을 추출합니다.
    
    Returns:
        지역명 또는 None
    """
    # 간단한 키워드 매칭
    regions = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
        "수원", "성남", "고양", "용인", "부천", "안산", "안양", "남양주",
        "순천", "목포", "여수", "경주", "하남", "달서구", "팔달구"
    ]
    
    for region in regions:
        if region in user_message:
            return region
    
    return None