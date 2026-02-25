from architecture_agent.ingestion.resolve_abbr import (
    extract_abbreviations_by_law,
    merge_abbreviation_maps,
    resolve_abbreviations,
)
from architecture_agent.schemas import ArticleChunk


def test_abbreviation_maps_are_separated_by_law():
    law_chunk = ArticleChunk(
        law_name="건축법",
        law_id="1823",
        law_type="법률",
        article_num="1",
        article_title="정의",
        content='「건축위원회 A」(이하 "위원회"라 한다). 위원회는 심의한다.',
    )
    decree_chunk = ArticleChunk(
        law_name="건축법 시행령",
        law_id="2118",
        law_type="시행령",
        article_num="1",
        article_title="정의",
        content='「건축위원회 B」(이하 "위원회"라 한다). 위원회는 의결한다.',
    )

    chunks = [law_chunk, decree_chunk]
    maps = extract_abbreviations_by_law(chunks)
    resolve_abbreviations(chunks, maps)

    assert maps["건축법"]["위원회"] == "건축위원회 A"
    assert maps["건축법 시행령"]["위원회"] == "건축위원회 B"

    assert "건축위원회 A" in law_chunk.content_resolved
    assert "건축위원회 B" in decree_chunk.content_resolved

    assert law_chunk.abbreviations["위원회"] == "건축위원회 A"
    assert decree_chunk.abbreviations["위원회"] == "건축위원회 B"


def test_abbreviation_keeps_article_reference_context():
    chunk = ArticleChunk(
        law_name="건축법",
        law_id="1823",
        law_type="법률",
        article_num="4",
        article_title="건축위원회",
        content='제4조에 따른 건축위원회(이하 "위원회"라 한다)는 심의한다.',
    )
    maps = extract_abbreviations_by_law([chunk])
    resolve_abbreviations([chunk], maps)

    assert maps["건축법"]["위원회"].startswith("건축법 제4조에 따른")
    assert "건축법 제4조에 따른 건축위원회" in chunk.content_resolved


def test_merge_abbreviation_prefers_higher_quality_expansion():
    base = {"위원회": "건축위원회"}
    new = {"위원회": "건축법 제4조에 따른 건축위원회"}
    merged = merge_abbreviation_maps(base, new)
    assert merged["위원회"] == "건축법 제4조에 따른 건축위원회"
