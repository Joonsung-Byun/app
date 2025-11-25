# Kids Chatbot 성능 평가 시스템

파인튜닝 전/후 성능을 측정하기 위한 평가 도구입니다.

## 폴더 구조

```
evaluation/
├── datasets/
│   ├── test_questions_prompt_aligned.json   # 기존 정합성 보강 데이터
│   └── test_questions_prompt_pruned.json    # 최신 평가용 (211문항)
├── scripts/
│   ├── evaluate_all.py        # 전체 평가 실행
│   ├── evaluate_rag.py        # RAG 검색 품질 평가
│   ├── evaluate_answer.py     # 답변 품질 평가 (LLM-as-Judge)
│   ├── evaluate_tools.py      # Tool 사용 정확도 평가
│   └── evaluate_system.py     # 시스템 성능 평가
│   └── eval_cases.py          # 케이스 분류/필터링 유틸
├── results/                   # 평가 결과 저장
├── requirements.txt           # 의존성
└── README.md
```

## 설치

```bash
cd evaluation
pip install -r requirements.txt
```

## 사용법

### 전체 평가 실행

```bash
# 모듈 실행 권장 (import 경로 문제 방지)
python -m evaluation.scripts.evaluate_all
```

### 옵션

```bash
# 샘플 크기 지정 (빠른 테스트용)
python -m evaluation.scripts.evaluate_all --sample 10

# 특정 평가만 스킵
python -m evaluation.scripts.evaluate_all --skip-answer --skip-tools

# 결과 저장 위치 지정
python -m evaluation.scripts.evaluate_all --output ./my_results
```

### 개별 평가 실행

```bash
# 답변 품질만 평가
python -m evaluation.scripts.evaluate_answer

# Tool 정확도만 평가
python -m evaluation.scripts.evaluate_tools

# 시스템 성능만 평가
python -m evaluation.scripts.evaluate_system
```

## 평가 항목

### 1. 서비스 품질 (케이스별)
- Case2(시설/RAG): Precision@3, Hit@3, 빈결과율
- Case3(fallback): RAG 0건 시 search_facilities→naver_web_search 호출 성공률
- No-tool: 도구 미사용 성공률
- Web: 시의성 질문에서 web_search 호출률

### 2. 검색 품질 (순수 RAG)
- **Precision@K**, **MRR** (Case2 rel 있는 문항만 대상)

### 3. 답변 품질 (LLM-as-Judge)

GPT-4o-mini를 사용하여 1-5점 평가:

- **정확성**: 사실적 정확성
- **관련성**: 질문에 적절한 답변인지
- **유용성**: 어린이에게 도움이 되는지

ground_truth는 **참고용**으로만 사용되며, 정확히 일치하지 않아도 의미적으로 맞으면 높은 점수를 받습니다.

### 4. Tool 사용 정확도

- **Tool 선택 정확도**: 올바른 Tool을 호출했는지 (Jaccard 유사도)
- **파라미터 정확도**: Tool에 올바른 파라미터를 전달했는지

### 5. 시스템 성능

- **응답 시간**: 평균, P50, P90, P99
- **메모리 사용량**: 초기, 피크, 최종
- **성공률**: 에러 없이 응답한 비율

## 테스트 데이터셋

`datasets/test_questions_prompt_pruned.json` (211개) 기준 분포:

| 카테고리   | 개수 | 설명                                  |
| ---------- | ---- | ------------------------------------- |
| weather    | 25   | 날씨 질문 (get_weather_forecast)      |
| complex    | 50   | 날씨+시설 복합 (get_weather_forecast+search_facilities) |
| places     | 60   | 시설 검색 (search_facilities)         |
| web_search | 44   | 시의성/웹 검색 (naver_web_search)     |
| map        | 20   | 지도 검색 (search_map_by_address/show_map_for_facilities) |
| general    | 12   | 무도구(검증용)                        |

케이스별 특수 집합:
- Case2 후기/리뷰 단어 포함 시설 검색: 20문항
- Case3 RAG→Web fallback: 20문항
- No-tool 검증: 12문항 (general 6 + Case4 6)

### 데이터셋 구조

```json
{
  "id": 1,
  "category": "weather",
  "question": "서울 날씨 어때?",
  "expected_tools": ["get_weather_forecast"],
  "expected_tool_params": { "location": "서울" },
  "ground_truth": "서울의 현재 날씨 정보",
  "relevant_doc_ids": []
}
```

### 필드 설명

- **expected_tools**: 이 질문에서 호출되어야 하는 도구 목록
- **expected_tool_params**: 도구에 전달되어야 하는 파라미터 (부분 일치로 평가)
- **ground_truth**: LLM-as-Judge가 답변 평가 시 참고하는 예상 정답
- **relevant_doc_ids**: RAG 평가용 관련 문서 ID 목록

## 지원하는 도구

평가 시스템은 다음 6개의 백엔드 도구를 커버합니다:

1. **get_weather_forecast**: 날씨 조회
2. **search_facilities**: 시설 검색 (RAG)
3. **naver_web_search**: 네이버 웹 검색
4. **search_map_by_address**: 지도 위치 검색
5. **show_map_for_facilities**: 시설 지도 표시
6. **extract_user_intent**: 사용자 의도 추출

## 결과 해석

### 파인튜닝 방향 결정 기준

| 문제           | 낮은 점수 지표                 | 해결 방향                         |
| -------------- | ------------------------------ | --------------------------------- |
| 검색 품질 저하 | RAG Precision/Recall           | Embedding 모델 파인튜닝           |
| Tool 선택 오류 | Tool Selection Accuracy        | Function calling 학습 데이터 추가 |
| 답변 품질 저하 | Answer Quality (정확성/유용성) | Instruction tuning                |
| 느린 응답      | Latency P90/P99                | 모델 경량화 또는 캐싱             |

## 베이스라인 측정

파인튜닝 전 현재 성능을 베이스라인으로 저장:

```bash
python scripts/evaluate_all.py --output results/baseline
```

파인튜닝 후 비교:

```bash
python scripts/evaluate_all.py --output results/finetuned
```

## 주의사항

1. **API 비용**: 답변 품질 평가는 GPT-4o-mini API를 사용합니다.
2. **실행 시간**: 200개 질문 전체 평가는 약 60-120분 소요됩니다.
3. **환경 변수**: `OPENAI_API_KEY`가 설정되어 있어야 합니다.
4. **Tool 로깅**: Tool 정확도 평가를 위해 agent에 콜백 핸들러를 연결해야 합니다.
