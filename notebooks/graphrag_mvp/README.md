# graphrag_mvp

`research_mvp`(LangGraph/RAG)와 분리된 GraphRAG 실험 공간입니다.

## Notebook 순서
1. `01_load_sources.ipynb`  
데이터 소스 로드 및 상태 확인
2. `02_build_graph_payload.ipynb`  
`001823(건축법)`, `002118(건축법 시행령)` 대상 그래프 payload 생성  
노드: `Document`, `Article`, `Paragraph` / 관계: `REF`
3. `03_ingest_neo4j.ipynb`  
Neo4j 제약조건 생성 + 노드/엣지 적재
4. `04_query_graphrag.ipynb`  
질문 입력 후 REF 그래프 조회 실험
5. `05_vector_graph_rag.ipynb`  
NAVER 모델(`ClovaXEmbeddings`, `ChatClovaX`) 기반 Vector + Graph RAG 실험

## 경로 정책
- 공통 데이터 루트: `notebooks/research_mvp/data/processed`
- 현재 `graphrag_mvp`는 ref 중심 실험(appendix/abbreviation 미사용)
