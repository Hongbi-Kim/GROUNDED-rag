from __future__ import annotations

import json
import re
from pathlib import Path

from architecture_agent.schemas import ArticleChunk

ABBREVIATION_PATTERNS = [
    re.compile(r"「([^」]+)」\s*\(이하\s*[\"“]([^\"”]+)[\"”]\s*(?:이라|라)\s*한다\)"),
    re.compile(r"([^()\n]{2,}?)\s*\(이하\s*[\"“]([^\"”]+)[\"”]\s*(?:이라|라)\s*한다\)"),
    re.compile(r"([^,\n]{2,}?)을?\s*이하\s*[\"“]([^\"”]+)[\"”]"),
]

ARTICLE_REF_PATTERN = re.compile(
    r"(제\d+(?:의\d+)?조(?:제\d+항)?(?:제\d+호)?)(?:에\s*따른|에\s*따라|의)?\s*(.+)"
)


def _normalize_long_name(long_name: str, law_name: str) -> str:
    text = re.sub(r"\s+", " ", long_name).strip(" \t\n\r.,;:[]()「」")
    m = ARTICLE_REF_PATTERN.match(text)
    if not m:
        return text
    ref = m.group(1).strip()
    subject = m.group(2).strip(" \t\n\r.,;:")
    if not subject:
        return text
    return f"{law_name} {ref}에 따른 {subject}"


def _abbr_quality_score(expansion: str) -> int:
    score = min(len(expansion), 120)
    if ARTICLE_REF_PATTERN.match(expansion):
        score += 50
    if "제" in expansion and "조" in expansion:
        score += 20
    return score


def sanitize_abbreviation_map(law_name: str, abbr_map: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for short, long_name in abbr_map.items():
        s = (short or "").strip()
        l = (long_name or "").strip()
        if not s or not l:
            continue
        cleaned[s] = _normalize_long_name(l, law_name=law_name)
    return cleaned


def merge_abbreviation_maps(
    base_map: dict[str, str],
    new_map: dict[str, str],
) -> dict[str, str]:
    merged = dict(base_map)
    scores = {k: _abbr_quality_score(v) for k, v in merged.items()}
    for short, expansion in new_map.items():
        score = _abbr_quality_score(expansion)
        if short not in merged or score > scores.get(short, -1):
            merged[short] = expansion
            scores[short] = score
    return merged


def extract_abbreviations_by_law(chunks: list[ArticleChunk]) -> dict[str, dict[str, str]]:
    law_to_texts: dict[str, list[str]] = {}
    for chunk in chunks:
        law_to_texts.setdefault(chunk.law_name, []).append(chunk.content)

    law_abbr_maps: dict[str, dict[str, str]] = {}
    for law_name, texts in law_to_texts.items():
        full_text = "\n".join(texts)
        abbr_map: dict[str, str] = {}
        score_map: dict[str, int] = {}

        for pattern in ABBREVIATION_PATTERNS:
            for m in pattern.finditer(full_text):
                long_name = _normalize_long_name(m.group(1).strip(), law_name=law_name)
                short_name = m.group(2).strip()
                if short_name and long_name:
                    score = _abbr_quality_score(long_name)
                    if short_name not in abbr_map or score > score_map[short_name]:
                        abbr_map[short_name] = long_name
                        score_map[short_name] = score

        law_abbr_maps[law_name] = sanitize_abbreviation_map(law_name, abbr_map)
    return law_abbr_maps


def save_abbreviation_maps_by_law(
    law_abbr_maps: dict[str, dict[str, str]],
    output_path: str = "data/processed/abbr_maps_by_law.json",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(law_abbr_maps, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def chunk_key(chunk: ArticleChunk) -> str:
    return f"{chunk.law_id}:{chunk.article_num}"


def save_abbreviation_maps_by_chunk(
    chunk_abbr_maps: dict[str, dict[str, str]],
    output_path: str = "data/processed/abbr_maps_by_chunk.json",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chunk_abbr_maps, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def resolve_abbreviations_by_chunk(
    chunks: list[ArticleChunk],
    chunk_abbr_maps: dict[str, dict[str, str]],
) -> None:
    for chunk in chunks:
        abbr_map = chunk_abbr_maps.get(chunk_key(chunk), {})
        chunk.abbreviations = sanitize_abbreviation_map(chunk.law_name, abbr_map)
        pairs = sorted(chunk.abbreviations.items(), key=lambda x: len(x[0]), reverse=True)
        text = chunk.content
        for short, full in pairs:
            if len(short) <= 2:
                pattern = rf"(?<![가-힣A-Za-z0-9]){re.escape(short)}(?=\s|제|의|에|을|를|이|가|은|는|과|와|으로|$)"
            else:
                pattern = re.escape(short)
            text = re.sub(pattern, full, text)
        chunk.content_resolved = text


def resolve_abbreviations(
    chunks: list[ArticleChunk],
    law_abbr_maps: dict[str, dict[str, str]],
) -> None:
    for chunk in chunks:
        abbr_map = law_abbr_maps.get(chunk.law_name, {})
        chunk.abbreviations = abbr_map
        pairs = sorted(abbr_map.items(), key=lambda x: len(x[0]), reverse=True)
        text = chunk.content
        for short, full in pairs:
            if len(short) <= 2:
                pattern = rf"(?<![가-힣A-Za-z0-9]){re.escape(short)}(?=\s|제|의|에|을|를|이|가|은|는|과|와|으로|$)"
            else:
                pattern = re.escape(short)
            text = re.sub(pattern, full, text)
        chunk.content_resolved = text
