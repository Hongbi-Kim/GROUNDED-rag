from __future__ import annotations

import os

from langchain_naver import ChatClovaX

from architecture_agent.agent.graph import build_graph
from architecture_agent.agent.tools import Appendix1Index, LawRetriever, build_tools


def build_runtime(
    collection_name: str = "building_law",
    qdrant_path: str = "./qdrant_data",
    qdrant_url: str | None = None,
    qdrant_api_key: str | None = None,
    qdrant_prefer_grpc: bool = False,
    appendix_json: str = "data/processed/appendix1_terms.json",
):
    retriever = LawRetriever(
        collection_name=collection_name,
        qdrant_path=qdrant_path,
        qdrant_url=qdrant_url or os.getenv("QDRANT_URL"),
        qdrant_api_key=qdrant_api_key or os.getenv("QDRANT_API_KEY"),
        prefer_grpc=qdrant_prefer_grpc,
    )
    appendix = Appendix1Index(json_path=appendix_json)
    tool_list = build_tools(retriever=retriever, appendix_index=appendix)
    tool_map = {t.name: t for t in tool_list}

    llm = ChatClovaX(model="HCX-005")
    app = build_graph(tools=tool_map, llm=llm)
    return app


if __name__ == "__main__":
    app = build_runtime()
    output = app.invoke(
        {
            "user_query": "서울특별시 종로구 조건에서 건축선을 알려줘. 용도는 문화 및 집회시설, 도로너비 8",
            "confirmed_conditions": {},
            "max_hops": 3,
        }
    )
    print(output.get("final_answer", ""))
