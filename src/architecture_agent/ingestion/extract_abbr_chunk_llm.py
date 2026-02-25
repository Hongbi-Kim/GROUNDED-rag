from __future__ import annotations

import json
import re
from collections import defaultdict

from architecture_agent.ingestion.resolve_abbr import (
    chunk_key,
    merge_abbreviation_maps,
    sanitize_abbreviation_map,
)
from architecture_agent.schemas import ArticleChunk


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _parse_abbr_json(text: str) -> dict[str, str]:
    raw = _strip_code_fence(text)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if isinstance(obj, dict) and isinstance(obj.get("abbreviations"), dict):
        obj = obj["abbreviations"]

    if not isinstance(obj, dict):
        return {}

    out: dict[str, str] = {}
    for k, v in obj.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def extract_abbreviations_by_chunk_llm(
    chunks: list[ArticleChunk],
    llm=None,
    model: str = "HCX-005",
    max_chars_per_chunk: int = 5000,
) -> dict[str, dict[str, str]]:
    if llm is None:
        from langchain_naver import ChatClovaX

        llm = ChatClovaX(model=model)

    chunk_maps: dict[str, dict[str, str]] = {}
    for chunk in chunks:
        text = chunk.content[:max_chars_per_chunk]
        prompt = (
            "다음 단일 조문에서 정의된 축약어만 JSON으로 추출하라.\n"
            "반드시 축약어 키와 확장명 값만 포함하고, 모르면 빈 JSON을 반환하라.\n"
            "규칙:\n"
            "1) 축약어 패턴은 보통 '(이하 \"X\"이라 한다)'\n"
            "2) 값은 가능한 완전한 명칭으로 작성\n"
            "3) 출력은 JSON 객체만\n"
            "예시: {\"위원회\": \"건축법 제4조에 따른 건축위원회\"}\n\n"
            f"법령명: {chunk.law_name}\n"
            f"조문: 제{chunk.article_num}조\n"
            f"제목: {chunk.article_title}\n"
            f"본문:\n{text}"
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", str(response))
        parsed = _parse_abbr_json(content)
        chunk_maps[chunk_key(chunk)] = sanitize_abbreviation_map(chunk.law_name, parsed)

    return chunk_maps


def aggregate_chunk_abbr_maps_by_law(
    chunks: list[ArticleChunk],
    chunk_maps: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    by_law: dict[str, dict[str, str]] = defaultdict(dict)
    index = {chunk_key(c): c for c in chunks}
    for ckey, cmap in chunk_maps.items():
        chunk = index.get(ckey)
        if not chunk:
            continue
        law_name = chunk.law_name
        by_law[law_name] = merge_abbreviation_maps(by_law[law_name], cmap)
    return dict(by_law)
