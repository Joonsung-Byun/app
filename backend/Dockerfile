# 1. 베이스 이미지: 파이썬 3.10 슬림 버전을 사용합니다.
FROM python:3.10-slim

# 2. 작업 디렉토리: 컨테이너 내부의 /app 폴더를 기본 폴더로 지정합니다.
WORKDIR /app

# 3. 의존성 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 복사
COPY . .

# 5. 포트 개방
EXPOSE 8080

# 6. 서버 실행
# 컨테이너가 시작될 때 이 명령어를 실행합니다.
# uvicorn을 사용해 main.py 파일의 app 객체를 실행합니다.
# --host 0.0.0.0 은 컨테이너 외부에서의 접속을 허용합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]