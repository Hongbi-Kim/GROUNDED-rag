from architecture_agent.ingestion.extract_refs import extract_references
from architecture_agent.schemas import ArticleChunk


def test_extract_references_internal_external_parent():
    chunk = ArticleChunk(
        law_name="건축법 시행령",
        law_id="2118",
        law_type="시행령",
        article_num="31",
        article_title="테스트",
        content=(
            "「국토의 계획 및 이용에 관한 법률」 제36조에 따른다. "
            "제2조제1항제11호를 준용한다. "
            "법 제46조제1항에 따라 정한다."
        ),
    )

    extract_references([chunk])

    assert any(r.ref_type == "external" and r.article == "36" for r in chunk.external_refs)
    assert any(r.ref_type == "internal" and r.article == "2" and r.paragraph == "1" for r in chunk.internal_refs)
    assert any(r.ref_type == "parent" and r.article == "46" and r.paragraph == "1" for r in chunk.parent_law_refs)
