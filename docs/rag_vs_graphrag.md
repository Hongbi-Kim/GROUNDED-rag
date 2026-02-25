# RAG vs GraphRAG 정리

## 1. 목적
건축 법률 질의응답에서 두 접근을 병행 실험한다.
- LangGraph 기반 RAG
- Neo4j 기반 GraphRAG

목표는 `정확도(근거 일치)`와 `참조 추적 신뢰성`을 높이는 것이다.

## 2. 용어 정의
### LangGraph RAG
질문 -> 조건/의도 파싱 -> 벡터 검색 -> 참조 확장 -> 답변 생성 파이프라인을 상태 그래프로 제어하는 방식.

### Neo4j GraphRAG
법률 데이터를 그래프 노드/엣지로 저장하고, 질의 시 벡터 검색 + 그래프 참조(REF) 탐색을 결합하는 방식.

## 3. 현재 구현 상태
### A. LangGraph RAG (research_mvp)
- 위치: `notebooks/research_mvp/06_run_agent.ipynb`
- 데이터: Qdrant + ref/abbr/appendix 보조 파일
- 강점: 빠른 MVP 반복, 체인 디버깅 쉬움
- 한계: 참조 경로/구조를 DB 레벨에서 명시적으로 관리하기 어려움

### B. Neo4j GraphRAG (graphrag_mvp)
- 위치: `notebooks/graphrag_mvp`
- 현재 스키마:
  - 노드: `Law`, `Article`, `Paragraph`
  - 구조 엣지: `HAS_ARTICLE`, `HAS_PARAGRAPH`
  - 참조 엣지: `REF` (단일)
- Ref 처리:
  - `법-only ref` -> `Article -> Law`
  - `법+조 ref` -> `Article -> Article`
  - `법+조+항 ref` -> `Article -> Paragraph`
  - 대상 본문이 없어도 placeholder 노드 생성 가능

## 4. 데이터 범위(현재)
- Source 본문 적재: 건축법(`001823`), 건축법 시행령(`002118`)
- Ref 타겟: 위 소스에서 추출된 참조를 기준으로 `Law/Article/Paragraph` 노드 확장

## 5. 검색/추론 흐름 비교
### LangGraph RAG
1. 질문 분석
2. 벡터 검색
3. 필요시 ref 추적
4. LLM 답변 생성

### Neo4j GraphRAG
1. Paragraph 벡터 검색(seed)
2. seed Paragraph의 parent Article 도출
3. `REF` 탐색으로 Article/Paragraph/Law 확장
4. 확장된 문맥으로 LLM 답변 생성

## 6. 장단점 비교
### LangGraph RAG
- 장점: 구성 유연, 빠른 실험
- 단점: 참조 구조를 일관되게 재사용/검증하기 어려움

### Neo4j GraphRAG
- 장점: 참조 구조 명시화, hop 기반 추론/시각화 유리
- 단점: 스키마/적재/마이그레이션 관리 비용 증가

## 7. 평가 항목 (공통)
- 근거 일치율: 답변 근거 조문이 실제 검색 문맥과 맞는가
- 참조 회수율: 필요한 REF를 놓치지 않는가
- 과참조율: 불필요한 REF 확장 비율
- 지연시간: 응답 시간
- 운영 안정성: 재실행/재적재 시 충돌 여부

## 8. 최근 이슈/결정
- 관계명은 `REF`로 단일화
- 노드는 `Law -> Article -> Paragraph` 계층으로 통일
- 과거 스키마 제약 충돌(`Law.law_id`) 대응을 위해 ingest 단계에 레거시 정리 셀 추가
- 임베딩은 `Paragraph.embedding`에 저장, 기존 값은 pass하도록 재시도/스킵 로직 적용

## 9. 다음 액션
1. 질의셋(건축선/용적률/건폐율/주차 등) 기준으로 두 방식 A/B 테스트
2. `법-only ref` 확장 전략(해당 법 내 추가 vector search) 실험
3. 결과를 이 문서에 날짜/설정/결과 형태로 누적 기록
