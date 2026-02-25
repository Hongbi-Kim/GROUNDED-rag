from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_PDF_PATH = "data/[별표 1] 용도별 건축물의 종류(제3조의5 관련)(건축법 시행령).pdf"
DEFAULT_OUT_PATH = "data/processed/appendix1_terms.json"

# Minimal seed for stable runtime lookup; can be expanded from PDF parsing.
SEED_TERMS = [
    {
        "category": "문화 및 집회시설",
        "subcategory": "공연장",
        "aliases": ["문화시설", "집회시설", "공연시설"],
        "description": "공연, 집회, 관람 등 다중 이용 목적의 시설군.",
        "source_clause": "건축법 시행령 [별표 1]",
    },
    {
        "category": "문화 및 집회시설",
        "subcategory": "집회장",
        "aliases": ["전시장", "회의장"],
        "description": "회의, 전시, 행사 등 집회 기능 중심 시설.",
        "source_clause": "건축법 시행령 [별표 1]",
    },
    {
        "category": "주거시설",
        "subcategory": "공동주택",
        "aliases": ["아파트", "연립주택", "다세대주택"],
        "description": "다수 세대의 주거를 위한 건축물.",
        "source_clause": "건축법 시행령 [별표 1]",
    },
    {
        "category": "업무시설",
        "subcategory": "일반업무시설",
        "aliases": ["사무소", "오피스"],
        "description": "사무 및 업무 수행 목적의 시설.",
        "source_clause": "건축법 시행령 [별표 1]",
    },
]


def _normalize_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _extract_terms_from_text(text: str) -> list[dict]:
    terms: list[dict] = []
    current_category = ""
    for raw_line in text.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            continue
        if "시설" in line and len(line) < 40 and not line.startswith("-"):
            current_category = line
            continue
        bullet_match = re.match(r"^(\d+\.|[가-힣]\.|\-)?\s*(.+)$", line)
        if not bullet_match:
            continue
        body = bullet_match.group(2)
        if len(body) < 3:
            continue
        if current_category:
            terms.append(
                {
                    "category": current_category,
                    "subcategory": body[:50],
                    "aliases": [],
                    "description": body,
                    "source_clause": "건축법 시행령 [별표 1]",
                }
            )
    return terms


def _extract_pdf_text(pdf_path: str) -> str:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return ""

    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def build_appendix1_json(
    pdf_path: str = DEFAULT_PDF_PATH,
    output_path: str = DEFAULT_OUT_PATH,
) -> Path:
    extracted_text = _extract_pdf_text(pdf_path)
    parsed_terms = _extract_terms_from_text(extracted_text) if extracted_text else []

    merged = {(t["category"], t["subcategory"]): t for t in SEED_TERMS}
    for term in parsed_terms:
        key = (term["category"], term["subcategory"])
        merged.setdefault(key, term)

    output = {
        "source": "건축법 시행령 [별표 1]",
        "version": "mvp",
        "terms": list(merged.values()),
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    path = build_appendix1_json()
    print(f"saved: {path}")
