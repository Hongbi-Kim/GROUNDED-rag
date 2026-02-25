from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, TypedDict


RefType = Literal["internal", "external", "parent"]


@dataclass
class Reference:
    ref_type: RefType
    law_name: str | None
    article: str
    paragraph: str | None = None
    item: str | None = None
    raw: str = ""


@dataclass
class ArticleChunk:
    law_name: str
    law_id: str
    article_num: str
    article_title: str
    content: str
    content_resolved: str = ""
    paragraphs: list[dict] = field(default_factory=list)
    internal_refs: list[Reference] = field(default_factory=list)
    external_refs: list[Reference] = field(default_factory=list)
    parent_law_refs: list[Reference] = field(default_factory=list)
    abbreviations: dict[str, str] = field(default_factory=dict)
    effective_date: str = ""
    change_type: str = ""
    law_type: str = ""

    def to_payload(self) -> dict:
        return {
            "law_name": self.law_name,
            "law_id": self.law_id,
            "law_type": self.law_type,
            "article_num": self.article_num,
            "article_title": self.article_title,
            "content_original": self.content,
            "paragraphs": self.paragraphs,
            "internal_refs": [asdict(r) for r in self.internal_refs],
            "external_refs": [asdict(r) for r in self.external_refs],
            "parent_law_refs": [asdict(r) for r in self.parent_law_refs],
            "abbreviations": self.abbreviations,
            "effective_date": self.effective_date,
            "change_type": self.change_type,
        }


class ConditionSlots(TypedDict, total=False):
    address: str
    usage: str
    site_area_m2: float
    gross_floor_area_m2: float
    floors: str
    max_height_m: float
    road_width_m: float


class AgentState(TypedDict, total=False):
    user_query: str
    confirmed_conditions: ConditionSlots
    missing_slots: list[str]
    intent: str
    search_queries: list[str]
    retrieved_articles: list[dict]
    pending_refs: list[Reference]
    resolved_refs: list[Reference]
    hop_count: int
    max_hops: int
    all_context: list[dict]
    appendix_context: list[dict]
    calculation_result: str
    calc_trace: str
    citation_map: list[dict]
    final_answer: str
