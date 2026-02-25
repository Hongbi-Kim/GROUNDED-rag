from architecture_agent.ingestion.extract_abbr_chunk_llm import (
    aggregate_chunk_abbr_maps_by_law,
    extract_abbreviations_by_chunk_llm,
)
from architecture_agent.schemas import ArticleChunk


class DummyResp:
    def __init__(self, content: str):
        self.content = content


class DummyLLM:
    def __init__(self):
        self.calls = 0

    def invoke(self, _prompt: str):
        self.calls += 1
        if self.calls == 1:
            return DummyResp('{"위원회": "건축법 제4조에 따른 건축위원회"}')
        return DummyResp('{"위원회": "건축법 시행령 제5조에 따른 건축위원회"}')


def test_extract_abbreviations_by_chunk_llm_and_aggregate():
    chunks = [
        ArticleChunk(
            law_name="건축법",
            law_id="1823",
            law_type="법률",
            article_num="4",
            article_title="건축위원회",
            content='제4조에 따른 건축위원회(이하 "위원회"라 한다).',
        ),
        ArticleChunk(
            law_name="건축법 시행령",
            law_id="2118",
            law_type="시행령",
            article_num="5",
            article_title="위원회 구성",
            content='제5조에 따른 건축위원회(이하 "위원회"라 한다).',
        ),
    ]

    chunk_maps = extract_abbreviations_by_chunk_llm(chunks, llm=DummyLLM())
    assert chunk_maps["1823:4"]["위원회"].startswith("건축법 제4조")
    assert chunk_maps["2118:5"]["위원회"].startswith("건축법 시행령 제5조")

    by_law = aggregate_chunk_abbr_maps_by_law(chunks, chunk_maps)
    assert by_law["건축법"]["위원회"].startswith("건축법 제4조")
    assert by_law["건축법 시행령"]["위원회"].startswith("건축법 시행령 제5조")
