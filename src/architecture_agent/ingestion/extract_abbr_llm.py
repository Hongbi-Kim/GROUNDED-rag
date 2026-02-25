from __future__ import annotations

import json
import re
from collections import defaultdict

from architecture_agent.ingestion.resolve_abbr import sanitize_abbreviation_map
from architecture_agent.schemas import ArticleChunk


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _build_context(chunks: list[ArticleChunk], max_chars: int = 20000) -> str:
    joined = "\n\n".join(
        f"[{c.article_num}] {c.article_title}\n{c.content}" for c in chunks
    )
    return joined[:max_chars]


def _parse_llm_abbr_json(raw_text: str) -> dict[str, str]:
    text = _strip_code_fence(raw_text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}

    if isinstance(data, dict) and "abbreviations" in data and isinstance(data["abbreviations"], dict):
        data = data["abbreviations"]

    if not isinstance(data, dict):
        return {}

    out: dict[str, str] = {}
    for short, long_name in data.items():
        if isinstance(short, str) and isinstance(long_name, str):
            out[short] = long_name
    return out


def extract_abbreviations_by_law_llm(
    chunks: list[ArticleChunk],
    llm=None,
    model: str = "HCX-005",
    max_chars_per_law: int = 20000,
) -> dict[str, dict[str, str]]:
    if llm is None:
        from langchain_naver import ChatClovaX

        llm = ChatClovaX(model=model)

    grouped: dict[str, list[ArticleChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.law_name].append(chunk)

    results: dict[str, dict[str, str]] = {}

    for law_name, law_chunks in grouped.items():
        context = _build_context(law_chunks, max_chars=max_chars_per_law)
        prompt = (
            "다음 법령 텍스트에서 축약어 정의만 추출하라.\n"
            "규칙:\n"
            "1) 축약어가 아닌 일반 단어는 제외\n"
            "2) 값은 가능한 한 조항 정보를 포함해 완전한 명칭으로 작성\n"
            "3) JSON 객체만 출력\n"
            "출력 형식 예시: {\"법\": \"건축법\", \"위원회\": \"건축법 제4조에 따른 건축위원회\"}\n\n"
            f"법령명: {law_name}\n"
            f"텍스트:\n{context}"
        )

        response = llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        abbr_map = _parse_llm_abbr_json(content)
        results[law_name] = sanitize_abbreviation_map(law_name, abbr_map)

    return results
