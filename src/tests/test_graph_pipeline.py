from architecture_agent.agent.graph import (
    answer_generator,
    appendix1_tool_router,
    calculator_llm,
    condition_confirmer,
    condition_parser,
    intent_parser,
    law_retriever,
    reference_tracker,
)


class DummyTool:
    def __init__(self, fn):
        self._fn = fn

    def invoke(self, payload):
        return self._fn(payload)


def test_graph_nodes_for_architecture_line_flow():
    tools = {
        "search_law_chunks": DummyTool(
            lambda payload: [
                {
                    "content": "제46조 본문",
                    "metadata": {
                        "law_id": "1823",
                        "law_name": "건축법",
                        "article_num": "46",
                        "article_title": "건축선의 지정",
                        "internal_refs": [
                            {
                                "ref_type": "internal",
                                "law_name": "건축법",
                                "article": "2",
                                "paragraph": "1",
                                "item": "11",
                                "raw": "제2조제1항제11호",
                            }
                        ],
                    },
                }
            ]
        ),
        "get_article": DummyTool(
            lambda payload: [
                {
                    "content": "제2조 정의",
                    "metadata": {
                        "law_id": payload["law_id"],
                        "law_name": "건축법",
                        "article_num": payload["article_num"],
                        "article_title": "정의",
                        "internal_refs": [],
                    },
                }
            ]
        ),
        "find_children_by_parent_ref": DummyTool(lambda payload: []),
        "lookup_appendix1_term": DummyTool(
            lambda payload: [
                {
                    "category": "문화 및 집회시설",
                    "subcategory": "공연장",
                    "aliases": ["문화시설"],
                    "description": "공연 목적",
                    "source_clause": "건축법 시행령 [별표 1]",
                }
            ]
        ),
    }

    state = {
        "user_query": "서울시 종로구, 용도 문화 및 집회시설, 도로너비 8 조건에서 건축선을 알려줘",
        "confirmed_conditions": {},
        "max_hops": 3,
    }

    state = condition_parser(state)
    state = condition_confirmer(state)
    state = intent_parser(state)
    state = law_retriever(state, tools)
    state = reference_tracker(state, tools)
    state = appendix1_tool_router(state, tools)
    state = calculator_llm(state, llm=None)
    state = answer_generator(state)

    assert state["intent"] == "건축선"
    assert len(state["all_context"]) >= 2
    assert state["appendix_context"]
    assert "산식" in state["final_answer"]
