from __future__ import annotations

from architecture_agent.schemas import ArticleChunk


def normalize_to_list(value):
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return value
    return []


def normalize_paragraph_num(raw: str) -> str:
    circled_map = {
        "①": "1",
        "②": "2",
        "③": "3",
        "④": "4",
        "⑤": "5",
        "⑥": "6",
        "⑦": "7",
        "⑧": "8",
        "⑨": "9",
        "⑩": "10",
        "⑪": "11",
        "⑫": "12",
        "⑬": "13",
        "⑭": "14",
        "⑮": "15",
    }
    raw = (raw or "").strip()
    return circled_map.get(raw, raw)


def classify_law_type(law_name: str) -> str:
    if "시행규칙" in law_name:
        return "시행규칙"
    if "시행령" in law_name:
        return "시행령"
    return "법률"


def parse_article(article: dict, law_name: str, law_id: str) -> ArticleChunk | None:
    if article.get("조문여부") != "조문":
        return None

    article_num = str(article.get("조문번호", "")).strip()
    article_title = str(article.get("조문제목", "")).strip()
    article_header = str(article.get("조문내용", "")).strip()

    paragraphs_structured: list[dict] = []
    content_parts: list[str] = [article_header] if article_header else []

    for para in normalize_to_list(article.get("항")):
        para_num = normalize_paragraph_num(para.get("항번호", ""))
        para_content = str(para.get("항내용", "")).strip()
        if para_content:
            content_parts.append(para_content)

        subs_structured = []
        for sub in normalize_to_list(para.get("호")):
            sub_num = str(sub.get("호번호", "")).strip().rstrip(".")
            sub_content = str(sub.get("호내용", "")).strip()
            if sub_content:
                content_parts.append(sub_content)

            items_structured = []
            for item in normalize_to_list(sub.get("목")):
                item_num = str(item.get("목번호", "")).strip().rstrip(".")
                item_content = str(item.get("목내용", "")).strip()
                if item_content:
                    content_parts.append(item_content)
                items_structured.append({"num": item_num, "content": item_content})

            subs_structured.append(
                {"num": sub_num, "content": sub_content, "items": items_structured}
            )

        paragraphs_structured.append(
            {"num": para_num, "content": para_content, "subs": subs_structured}
        )

    return ArticleChunk(
        law_name=law_name,
        law_id=str(law_id),
        law_type=classify_law_type(law_name),
        article_num=article_num,
        article_title=article_title,
        content="\n".join([p for p in content_parts if p]),
        paragraphs=paragraphs_structured,
        effective_date=str(article.get("조문시행일자", "")),
        change_type=str(article.get("조문제개정유형", "")),
    )


def parse_law_data(data: dict) -> list[ArticleChunk]:
    law_info = data["법령"]["기본정보"]
    law_name = law_info["법령명_한글"]
    law_id = str(law_info["법령ID"])
    articles_raw = normalize_to_list(data["법령"]["조문"].get("조문단위"))

    chunks: list[ArticleChunk] = []
    for article in articles_raw:
        chunk = parse_article(article, law_name=law_name, law_id=law_id)
        if chunk:
            chunks.append(chunk)
    return chunks
