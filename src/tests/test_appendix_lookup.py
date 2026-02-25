import json
from pathlib import Path

from architecture_agent.agent.tools import Appendix1Index


def test_appendix_lookup_finds_culture_term(tmp_path):
    path = tmp_path / "appendix1_terms.json"
    path.write_text(
        json.dumps(
            {
                "source": "건축법 시행령 [별표 1]",
                "terms": [
                    {
                        "category": "문화 및 집회시설",
                        "subcategory": "공연장",
                        "aliases": ["문화시설"],
                        "description": "공연 목적 시설",
                        "source_clause": "건축법 시행령 [별표 1]",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    idx = Appendix1Index(str(path))
    result = idx.lookup("문화 및 집회시설")
    assert result
    assert result[0]["category"] == "문화 및 집회시설"
