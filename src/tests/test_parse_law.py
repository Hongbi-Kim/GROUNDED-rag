from architecture_agent.ingestion.parse_law import parse_law_data


def test_parse_law_handles_dict_and_list_mixed_structure():
    sample = {
        "법령": {
            "기본정보": {"법령명_한글": "건축법", "법령ID": "1823"},
            "조문": {
                "조문단위": {
                    "조문여부": "조문",
                    "조문번호": "46",
                    "조문제목": "건축선의 지정",
                    "조문내용": "제46조(건축선의 지정)",
                    "항": {
                        "항번호": "①",
                        "항내용": "도로와 접한 부분",
                        "호": {
                            "호번호": "1.",
                            "호내용": "세부 요건",
                            "목": {"목번호": "가.", "목내용": "목 내용"},
                        },
                    },
                }
            },
        }
    }

    chunks = parse_law_data(sample)
    assert len(chunks) == 1

    chunk = chunks[0]
    assert chunk.article_num == "46"
    assert chunk.paragraphs[0]["num"] == "1"
    assert chunk.paragraphs[0]["subs"][0]["num"] == "1"
    assert chunk.paragraphs[0]["subs"][0]["items"][0]["num"] == "가"
