# Node.js 20 버전을 기반으로 환경 구성
FROM node:20-alpine

# 작업 디렉토리 설정
WORKDIR /app

# package.json 파일들을 먼저 복사
COPY package*.json ./

# 라이브러리 설치
RUN npm install

# 현재 디렉토리(frontend)의 모든 파일을 컨테이너 /app으로 복사
COPY . .

# 포트 노출 (Vite 기본 포트)
EXPOSE 5173

# 컨테이너 실행 시 프론트엔드 서버 구동
CMD ["npm", "run", "dev", "--", "--host"]