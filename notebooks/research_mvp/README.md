# Research Notebooks (Self-contained)

요청 반영: 내부 모듈(`architecture_agent.*`) import 없이, 각 단계 코드를 노트북 셀에 직접 작성했습니다.

실행 순서:
1. `01_fetch_law.ipynb`
2. `02_parse_law.ipynb`
3. `03_refs_and_abbr.ipynb`
4. `04_build_appendix1_json.ipynb`
5. `05_index_qdrant.ipynb`
6. `06_run_agent.ipynb`

실행 전제:
- conda 환경: `natna`
- `.env`에 `OC` 설정
- Clova/Qdrant 관련 환경 설정


추가 산출물:
- `data/processed/abbr_maps_by_law.json`: 법령별 축약어 맵 저장 파일
