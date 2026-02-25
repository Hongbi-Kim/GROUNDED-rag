from __future__ import annotations

import re
from typing import Any

from architecture_agent.schemas import AgentState, Reference

INTENT_KEYWORDS = {
    "건축선": ["건축선", "도로 경계", "후퇴"],
    "용적률": ["용적률", "연면적"],
    "건폐율": ["건폐율", "건축면적"],
    "주차": ["주차", "주차대수"],
}

REQUIRED_SLOTS = [
    "address",
    "usage",
    "site_area_m2",
    "gross_floor_area_m2",
    "floors",
    "max_height_m",
    "road_width_m",
]


def _extract_number(text: str, label: str) -> float | None:
    pattern = rf"{label}\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)"
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def condition_parser(state: AgentState) -> AgentState:
    query = state.get("user_query", "")
    slots = dict(state.get("confirmed_conditions", {}))

    if "서울" in query or "구" in query or "시" in query:
        addr_match = re.search(r"([가-힣]+(?:시|도)\s*[가-힣]+(?:시|군|구))", query)
        if addr_match:
            slots["address"] = addr_match.group(1)

    usage_match = re.search(r"(문화 및 집회시설|업무시설|주거시설|공동주택)", query)
    if usage_match:
        slots["usage"] = usage_match.group(1)

    if "지하" in query or "지상" in query:
        floor_match = re.search(r"(지하\d+층\s*지상\d+층|지상\d+층)", query)
        if floor_match:
            slots["floors"] = floor_match.group(1)

    site = _extract_number(query, "대지면적")
    gfa = _extract_number(query, "연면적")
    height = _extract_number(query, "최고높이")
    road = _extract_number(query, "도로너비")

    if site is not None:
        slots["site_area_m2"] = site
    if gfa is not None:
        slots["gross_floor_area_m2"] = gfa
    if height is not None:
        slots["max_height_m"] = height
    if road is not None:
        slots["road_width_m"] = road

    state["confirmed_conditions"] = slots
    return state


def condition_confirmer(state: AgentState) -> AgentState:
    slots = state.get("confirmed_conditions", {})
    state["missing_slots"] = [k for k in REQUIRED_SLOTS if k not in slots]
    return state


def intent_parser(state: AgentState) -> AgentState:
    query = state.get("user_query", "")
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(k in query for k in keywords):
            state["intent"] = intent
            break
    else:
        state["intent"] = "일반"

    state["search_queries"] = [
        query,
        state["intent"],
        f"건축법 {state['intent']}",
    ]
    return state


def law_retriever(state: AgentState, tools: dict[str, Any]) -> AgentState:
    search = tools["search_law_chunks"]
    items = []
    for q in state.get("search_queries", []):
        items.extend(search.invoke({"query": q, "k": 4}))

    dedup = {}
    for item in items:
        meta = item.get("metadata", {})
        key = (meta.get("law_id"), meta.get("article_num"))
        dedup[key] = item

    result = list(dedup.values())
    state["retrieved_articles"] = result
    state["all_context"] = result.copy()

    pending: list[Reference] = []
    for item in result:
        for ref in item.get("metadata", {}).get("internal_refs", []):
            pending.append(Reference(**ref))
    state["pending_refs"] = pending
    state["resolved_refs"] = []
    state["hop_count"] = state.get("hop_count", 0)
    state["max_hops"] = state.get("max_hops", 3)
    return state


def reference_tracker(state: AgentState, tools: dict[str, Any]) -> AgentState:
    pending = list(state.get("pending_refs", []))
    resolved = list(state.get("resolved_refs", []))
    all_context = list(state.get("all_context", []))

    if not pending:
        return state

    get_article = tools["get_article"]
    find_children = tools["find_children_by_parent_ref"]

    current = pending.pop(0)
    docs = []

    if current.ref_type == "internal" and current.law_name:
        law_id = "1823" if current.law_name == "건축법" else "2118"
        docs = get_article.invoke({"law_id": law_id, "article_num": current.article})
    elif current.ref_type == "parent" and current.law_name:
        docs = find_children.invoke({"law_name": current.law_name, "article_num": current.article})

    if docs:
        all_context.extend(docs)
        resolved.append(current)

    state["pending_refs"] = pending
    state["resolved_refs"] = resolved
    state["all_context"] = all_context
    state["hop_count"] = state.get("hop_count", 0) + 1
    return state


def appendix1_tool_router(state: AgentState, tools: dict[str, Any]) -> AgentState:
    query = state.get("user_query", "")
    usage = state.get("confirmed_conditions", {}).get("usage", "")
    lookup = tools["lookup_appendix1_term"]

    term = usage or query
    state["appendix_context"] = lookup.invoke({"term_or_query": term})
    return state


def calculator_llm(state: AgentState, llm=None) -> AgentState:
    conditions = state.get("confirmed_conditions", {})
    context = state.get("all_context", [])[:6]

    prompt = (
        "너는 건축법률 계산 엔진이다. 근거 조항, 계산식, 중간값, 최종값을 모두 명시하라.\n"
        f"조건: {conditions}\n"
        f"질문: {state.get('user_query', '')}\n"
        f"컨텍스트 조항: {[c.get('metadata', {}).get('article_num') for c in context]}\n"
    )

    if llm is None:
        text = "근거: 건축법 관련 조항\n산식: 입력 조건 기반 계산\n중간값: N/A\n최종값: 추정 필요"
    else:
        response = llm.invoke(prompt)
        text = getattr(response, "content", str(response))

    state["calculation_result"] = text
    state["calc_trace"] = text
    return state


def answer_generator(state: AgentState) -> AgentState:
    citations = []
    for item in state.get("all_context", []):
        m = item.get("metadata", {})
        citations.append(
            {
                "law_name": m.get("law_name"),
                "article_num": m.get("article_num"),
                "article_title": m.get("article_title"),
            }
        )

    state["citation_map"] = citations
    missing = state.get("missing_slots", [])
    missing_line = ""
    if missing:
        missing_line = f"\n추가 필요 조건: {', '.join(missing)}"

    state["final_answer"] = (
        f"의도: {state.get('intent')}\n"
        f"계산 결과:\n{state.get('calculation_result', '')}\n"
        f"인용 조항 수: {len(citations)}{missing_line}"
    )
    return state


def build_graph(tools: dict[str, Any], llm=None):
    try:
        from langgraph.graph import END, StateGraph
    except Exception as exc:  # pragma: no cover
        raise ImportError("langgraph is required to build runtime graph") from exc

    graph = StateGraph(AgentState)

    graph.add_node("condition_parser", lambda s: condition_parser(s))
    graph.add_node("condition_confirmer", lambda s: condition_confirmer(s))
    graph.add_node("intent_parser", lambda s: intent_parser(s))
    graph.add_node("law_retriever", lambda s: law_retriever(s, tools=tools))
    graph.add_node("reference_tracker", lambda s: reference_tracker(s, tools=tools))
    graph.add_node("appendix1_tool_router", lambda s: appendix1_tool_router(s, tools=tools))
    graph.add_node("calculator_llm", lambda s: calculator_llm(s, llm=llm))
    graph.add_node("answer_generator", lambda s: answer_generator(s))

    graph.set_entry_point("condition_parser")
    graph.add_edge("condition_parser", "condition_confirmer")
    graph.add_edge("condition_confirmer", "intent_parser")
    graph.add_edge("intent_parser", "law_retriever")
    graph.add_edge("law_retriever", "reference_tracker")

    def route_refs(state: AgentState):
        if state.get("pending_refs") and state.get("hop_count", 0) < state.get("max_hops", 3):
            return "reference_tracker"
        return "appendix1_tool_router"

    graph.add_conditional_edges(
        "reference_tracker",
        route_refs,
        {
            "reference_tracker": "reference_tracker",
            "appendix1_tool_router": "appendix1_tool_router",
        },
    )
    graph.add_edge("appendix1_tool_router", "calculator_llm")
    graph.add_edge("calculator_llm", "answer_generator")
    graph.add_edge("answer_generator", END)

    return graph.compile()
