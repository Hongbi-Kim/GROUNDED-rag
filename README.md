# 건축법률 에이전트 (Architecture Law Agent)

건축법 관련 질의에서 `조건 + 법령 근거 + 계산 결과`를 제공하는 RAG 에이전트입니다.

## 1. 현재 설계 기준
- 운영 코드는 모두 `.py` 기준 (`src/architecture_agent/*`).
- `data.ipynb`는 실험/테스트 용도이며 운영 파이프라인에서 사용하지 않습니다.
- Qdrant 컬렉션은 단일 컬렉션 `building_law`만 사용합니다.
- `[별표 1]`은 DB에 넣지 않고 `data/processed/appendix1_terms.json`으로 관리합니다.
- `previous/` 디렉터리는 레거시이며 항상 무시합니다.

## 2. 기술 스택
- Python 3.11 (conda 환경: `natna`)
- LangChain
- LangGraph
- Qdrant
- langchain-naver (ClovaX)
- langchain-qdrant

## 3. 프로젝트 구조
```text
src/
  architecture_agent/
    schemas.py
    run_agent.py
    ingestion/
      fetch_law.py
      parse_law.py
      extract_refs.py
      resolve_abbr.py
      build_appendix1_json.py
      index_qdrant.py
      pipeline.py
    agent/
      tools.py
      graph.py
  tests/
    test_parse_law.py
    test_extract_refs.py
    test_appendix_lookup.py
    test_graph_pipeline.py
```

## 4. 데이터 범위
- 건축법: `law_id=1823`
- 건축법 시행령: `law_id=2118`
- 별표: `[별표 1] 용도별 건축물의 종류(제3조의5 관련)`

## 5. 데이터 모델 요약
`ArticleChunk` 주요 필드:
- `law_id`, `law_name`, `law_type`
- `article_num`, `article_title`
- `content`, `content_resolved`
- `abbreviations` (해당 chunk의 법령별 축약어 맵, 없으면 `{}`)
- `paragraphs`
- `internal_refs`, `external_refs`, `parent_law_refs`
- `effective_date`, `change_type`

`Reference` 구조:
- `ref_type` (`internal` | `external` | `parent`)
- `law_name`, `article`, `paragraph`, `item`, `raw`

## 6. Ingestion 파이프라인
순서:
1. `fetch_law.py`: 법령 API 호출 후 raw JSON 저장
2. `parse_law.py`: 조문/항/호/목 파싱 (`dict/list` 정규화)
3. `extract_refs.py`: 내부/외부/모법 참조 구조화 추출
4. `resolve_abbr.py`: 법령별 축약어 맵 생성 + JSON 저장 + 본문 치환
5. `index_qdrant.py`: 단일 컬렉션 `building_law` 적재
6. `build_appendix1_json.py`: 별표1 JSON 생성

축약어 산출물:
- `data/processed/abbr_maps_by_law.json`: 법령별 축약어 맵
- `data/processed/abbr_maps_by_chunk.json`: chunk별 축약어 맵 (`law_id:article_num` 키)
- Qdrant payload의 `abbreviations`: 해당 chunk 기준 축약어 맵

통합 실행:
```bash
conda run -n natna python -m architecture_agent.ingestion.pipeline
```

기본 축약어 추출 모드:
- `run_ingestion(abbr_mode="llm_chunk")`: LLM만 사용해 chunk별 축약어를 추출합니다.
- chunk별 축약어를 바로 payload `abbreviations`에 넣어 런타임 재탐색을 줄입니다.

## 7. 런타임 에이전트 파이프라인
질의 흐름:
1. `condition_parser`: 질문에서 조건 슬롯 추출
2. `condition_confirmer`: 누락 슬롯 추출
3. `intent_parser`: 주제 파악 (건축선/용적률/건폐율/주차 등)
4. `law_retriever`: Qdrant Dense 검색
5. `reference_tracker`: 참조 루프 추적 (`max_hops=3`)
6. `appendix1_tool_router`: 별표1 JSON 조회 라우팅
7. `calculator_llm`: LLM 계산
8. `answer_generator`: 근거+산식+중간값+결과 출력

실행:
```bash
conda run -n natna python -m architecture_agent.run_agent
```

### 7.1 0-hop 프로덕트 API (프론트 연동용)
- 파일: `src/architecture_agent/service/zero_hop.py`
- API: `src/architecture_agent/api/server.py`
- 특징:
  - 참조 확장(hop) 없이 `0-hop`으로만 문서 검색/답변
  - 응답에 `references`(관련 법/조항 + 본문 `full_text`) 포함
  - 프론트 우측 문서 뷰어에서 바로 원문 표시 가능

서버 실행:
```bash
conda run -n natna python -m architecture_agent.run_api
```

엔드포인트:
- `GET /health`
- `POST /api/v1/chat/ask` (`{ "query": "...", "k": 5 }`)

## 8. Tool 인터페이스
`src/architecture_agent/agent/tools.py`:
- `search_law_chunks(query, law_name=None, law_type=None, k=6)`
- `get_article(law_id, article_num)`
- `find_children_by_parent_ref(law_name, article_num)`
- `lookup_appendix1_term(term_or_query)`

`lookup_appendix1_term` 검색 우선순위:
1. 정확 매칭
2. 별칭 매칭
3. 키워드 유사도 매칭

## 9. 실행 환경 (conda: natna)
### 9.1 의존성 설치
```bash
conda run -n natna pip install -e .
conda run -n natna pip install -e .[dev]
```

### 9.2 환경변수
`.env`에 최소값 설정:
```env
OC=...
```

Clova/Qdrant 관련 환경변수는 사용 중인 SDK 설정에 맞춰 추가합니다.

Qdrant Cloud 사용 시 예시:
```env
QDRANT_URL=https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-east-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
```

코드는 `QDRANT_URL`이 설정되면 클라우드 연결을 우선 사용하고, 없으면 로컬 `qdrant_path`를 사용합니다.

프론트 연동 환경변수 (`.env` 또는 shell):
```env
VITE_AGENT_API_BASE=http://127.0.0.1:8000
```

## 10. 테스트
```bash
conda run -n natna pytest src/tests
```

검증 포인트:
- dict/list 혼합 구조 파싱 안정성
- 참조 추출 정확성
- 별표1 JSON 조회
- 조건 기반 건축선 질의 그래프 흐름

## 11. 운영 메모
- `data.ipynb`는 참고/실험용입니다.
- `data.py`는 초기 프로토타입 파일이며 운영 진입점은 `src/architecture_agent/*`입니다.
- 레거시 `previous/`는 읽지 않고 변경하지 않습니다.
