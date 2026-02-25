from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from architecture_agent.agent.tools import Appendix1Index, LawRetriever


TARGET_KEYWORDS = {
    "건축선": ["건축선", "도로경계", "후퇴선"],
    "건폐율": ["건폐율", "건축면적"],
    "용적률": ["용적률", "연면적"],
    "주차": ["주차", "주차대수", "주차장"],
}

LAW_NAME_TO_ID = {
    "건축법": "001823",
    "건축법 시행령": "002118",
    "건축법시행령": "002118",
}


@dataclass
class ZeroHopResult:
    answer: str
    targets: list[str]
    steps: list[str]
    references: list[dict[str, Any]]
    contexts_count: int
    trace: dict[str, Any]


class ZeroHopLawAgent:
    def __init__(
        self,
        collection_name: str = "building_law",
        qdrant_path: str = "./qdrant_data",
        qdrant_url: str | None = None,
        qdrant_api_key: str | None = None,
        qdrant_prefer_grpc: bool = False,
        appendix_json: str = "data/processed/appendix1_terms.json",
        answer_model: str = "HCX-005",
        answer_temperature: float = 0.0,
    ):
        load_dotenv()

        self.retriever = LawRetriever(
            collection_name=collection_name,
            qdrant_path=qdrant_path,
            qdrant_url=qdrant_url or os.getenv("QDRANT_URL"),
            qdrant_api_key=qdrant_api_key or os.getenv("QDRANT_API_KEY"),
            prefer_grpc=qdrant_prefer_grpc,
        )
        self.appendix = Appendix1Index(json_path=appendix_json)

        self.llm = None
        try:
            from langchain_naver import ChatClovaX

            self.llm = ChatClovaX(
                model=answer_model,
                temperature=answer_temperature,
                max_tokens=1200,
            )
        except Exception:
            self.llm = None

    @staticmethod
    def _chunk_key(meta: dict[str, Any]) -> str:
        return f"{str(meta.get('law_id', '')).zfill(6)}:{meta.get('article_num', '')}:{meta.get('article_sub', '0') or '0'}"

    @staticmethod
    def _normalize_text(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "")).strip()

    def extract_targets(self, query: str) -> list[str]:
        found: list[str] = []
        for target, kws in TARGET_KEYWORDS.items():
            if any(k in query for k in kws):
                found.append(target)
        return found or ["일반"]

    def retrieve_zero_hop(self, query: str, targets: list[str], k: int) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        per_query_k = max(k, 4)

        queries = [query]
        for t in targets:
            queries.append(t)
            queries.append(f"{query} {t}")

        for q in queries:
            docs.extend(self.retriever.similarity_search(q, k=per_query_k))

        dedup: dict[str, dict[str, Any]] = {}
        for d in docs:
            meta = d.get("metadata", {}) or {}
            key = self._chunk_key(meta)
            if key not in dedup:
                dedup[key] = d

        out = list(dedup.values())
        if len(out) < k:
            backfills = [f"건축법 {query}", f"건축법 시행령 {query}"]
            for bq in backfills:
                if len(out) >= k:
                    break
                for d in self.retriever.similarity_search(bq, k=max(k * 2, 8)):
                    meta = d.get("metadata", {}) or {}
                    key = self._chunk_key(meta)
                    if key not in dedup:
                        dedup[key] = d
                        out.append(d)

        return out[:k]

    def _build_references(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for d in docs:
            meta = d.get("metadata", {}) or {}
            content = str(d.get("content", ""))
            law_name = str(meta.get("law_name", ""))
            article_num = str(meta.get("article_num", ""))
            article_sub = str(meta.get("article_sub", "0") or "0")
            article_sub_txt = f"의{article_sub}" if article_sub not in ["", "0"] else ""
            title = str(meta.get("article_title", ""))
            section = f"제{article_num}조{article_sub_txt} {title}".strip()

            refs.append(
                {
                    "chunk_key": self._chunk_key(meta),
                    "document_name": law_name or "법령",
                    "section": section,
                    "law_id": str(meta.get("law_id", "")),
                    "law_name": law_name,
                    "article_num": article_num,
                    "article_sub": article_sub,
                    "article_title": title,
                    "content_preview": self._normalize_text(content)[:320],
                    "full_text": content,
                    "internal_refs": meta.get("internal_refs", []) or [],
                    "external_refs": meta.get("external_refs", []) or [],
                }
            )
        return refs

    def _is_answerable_without_refs(
        self,
        query: str,
        targets: list[str],
        contexts: list[dict[str, Any]],
    ) -> tuple[bool, str]:
        evidence = []
        for c in contexts[:5]:
            meta = c.get("metadata", {}) or {}
            evidence.append(
                {
                    "law_name": meta.get("law_name", ""),
                    "article_num": meta.get("article_num", ""),
                    "article_title": meta.get("article_title", ""),
                    "excerpt": self._normalize_text(c.get("content", ""))[:280],
                }
            )

        if self.llm is None:
            # fallback heuristic: 근거가 3개 이상이고 target 키워드가 본문에 있으면 우선 ref 없이 진행
            merged = " ".join([e["excerpt"] for e in evidence])
            has_target_signal = any(t in merged for t in targets if t != "일반")
            answerable = len(evidence) >= 3 and has_target_signal
            return answerable, "heuristic"

        prompt = (
            "너는 법률 QA의 ref 필요성 판단기다.\n"
            "중요: ref 내용을 미리 보지 말고, 현재 컨텍스트만으로 답변 가능한지 판단한다.\n"
            "기준:\n"
            "- 현재 컨텍스트만으로 질문의 판단/계산이 가능하면 answerable=true\n"
            "- 조문 이해를 위해 참조 법령/조항 해석이 필수면 answerable=false\n"
            "출력은 JSON만:\n"
            '{"answerable": true/false, "reason": "..."}\n\n'
            f"query: {query}\n"
            f"targets: {targets}\n"
            f"current_contexts: {evidence}\n"
        )
        raw = self.llm.invoke(prompt)
        text = getattr(raw, "content", str(raw)).strip()
        obj: dict[str, Any] = {}
        try:
            obj = json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    obj = json.loads(m.group(0))
                except Exception:
                    obj = {}
        answerable = bool(obj.get("answerable", False))
        reason = str(obj.get("reason", "")).strip() or text[:200]
        return answerable, reason

    @staticmethod
    def _parse_ref_article(article: str) -> str:
        a = str(article or "").strip()
        if not a:
            return ""
        m = re.fullmatch(r"\d+(?:의\d+)?", a)
        return a if m else ""

    def _resolve_ref_law_id(self, ref: dict[str, Any], source_meta: dict[str, Any]) -> str:
        law_name = str(ref.get("law_name", "") or "").strip()
        raw = str(ref.get("raw", "") or "")
        source_law_id = str(source_meta.get("law_id", "")).zfill(6)

        if law_name in LAW_NAME_TO_ID:
            return LAW_NAME_TO_ID[law_name]

        # 법령명 없이 '대통령령', '법' 등으로만 나오는 경우 보정
        if "대통령령" in raw or "시행령" in raw:
            return "002118"
        if re.search(r"\b법\b|법\s*제\d+", raw):
            return "001823"
        if "이 법" in raw:
            return source_law_id
        return ""

    def _extract_ref_candidates(self, contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen = set()

        for c in contexts:
            meta = c.get("metadata", {}) or {}
            source_key = self._chunk_key(meta)

            for r in (meta.get("internal_refs", []) or []):
                if not isinstance(r, dict):
                    continue
                law_id = str(meta.get("law_id", "")).zfill(6)
                article = self._parse_ref_article(r.get("article", ""))
                key = (law_id, article, source_key, "internal")
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "law_id": law_id,
                        "article": article,
                        "source": "internal",
                        "source_key": source_key,
                        "source_text": self._normalize_text(c.get("content", ""))[:900],
                        "raw": str(r.get("raw", "") or ""),
                        "law_name": str(meta.get("law_name", "") or ""),
                    }
                )

            for r in (meta.get("external_refs", []) or []):
                if not isinstance(r, dict):
                    continue
                law_id = self._resolve_ref_law_id(r, meta)
                if not law_id:
                    continue
                article = self._parse_ref_article(r.get("article", ""))
                key = (law_id, article, source_key, "external")
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "law_id": law_id,
                        "article": article,
                        "source": "external",
                        "source_key": source_key,
                        "source_text": self._normalize_text(c.get("content", ""))[:900],
                        "raw": str(r.get("raw", "") or ""),
                        "law_name": str(r.get("law_name", "") or ""),
                    }
                )

        # 우선순위: 조항 지정 ref > 법만 지정 ref
        out.sort(key=lambda x: (0 if x.get("article") else 1, x.get("source") != "internal"))
        return out

    def _should_follow_candidate_without_ref_content(
        self,
        query: str,
        targets: list[str],
        candidate: dict[str, Any],
    ) -> tuple[bool, int, str]:
        source = str(candidate.get("source_text", "") or "")
        raw_ref = str(candidate.get("raw", "") or "")
        ref_key = f"{candidate.get('law_id', '')}:{candidate.get('article', '') or '__law__'}"

        if self.llm is None:
            # fallback: chunk 내 명시 참조가 있고 현재 chunk에 target 키워드가 있으면 follow
            has_target = any(t in source for t in targets if t != "일반")
            follow = bool(raw_ref) and has_target
            return follow, (2 if follow else 0), "heuristic_without_ref_content"

        prompt = (
            "너는 법률 참조 추적 판단기다.\n"
            "중요: ref 조문 본문은 아직 읽지 않는다. 현재 chunk 맥락만으로 판단한다.\n"
            "출력은 JSON만:\n"
            '{"follow": true/false, "priority": 0|1|2, "reason": "..."}\n\n'
            f"query: {query}\n"
            f"targets: {targets}\n"
            f"current_chunk_preview: {source}\n"
            f"raw_ref: {raw_ref}\n"
            f"ref_key: {ref_key}\n"
        )
        raw = self.llm.invoke(prompt)
        text = getattr(raw, "content", str(raw)).strip()
        obj: dict[str, Any] = {}
        try:
            obj = json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    obj = json.loads(m.group(0))
                except Exception:
                    obj = {}
        follow = bool(obj.get("follow", obj.get("expand", False)))
        pri = obj.get("priority", 0)
        priority = int(pri) if str(pri).isdigit() else 0
        reason = str(obj.get("reason", "")).strip() or text[:160]
        return follow, max(0, min(priority, 2)), f"precheck_without_ref_content: {reason}"

    def _retrieve_related_chunks_in_law(
        self,
        query: str,
        targets: list[str],
        law_id: str,
        k: int = 2,
    ) -> list[dict[str, Any]]:
        qs = [query] + targets + [f"{query} {' '.join(targets)}"]
        dedup: dict[str, dict[str, Any]] = {}
        for q in qs:
            for d in self.retriever.similarity_search(q, k=max(6, k * 3)):
                meta = d.get("metadata", {}) or {}
                if str(meta.get("law_id", "")).zfill(6) != str(law_id).zfill(6):
                    continue
                key = self._chunk_key(meta)
                if key not in dedup:
                    dedup[key] = d
                if len(dedup) >= k:
                    break
            if len(dedup) >= k:
                break
        return list(dedup.values())[:k]

    def _expand_refs_if_needed(
        self,
        query: str,
        targets: list[str],
        contexts: list[dict[str, Any]],
        max_ref_expand: int = 4,
    ) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
        answerable, reason = self._is_answerable_without_refs(query, targets, contexts)
        trace: dict[str, Any] = {
            "precheck_answerable": bool(answerable),
            "precheck_reason": reason,
            "candidates_total": 0,
            "candidates_followed": 0,
            "expanded_ref_count": 0,
            "follow_checks": [],
        }
        if answerable:
            return contexts, f"skip_ref: {reason}", trace

        candidates = self._extract_ref_candidates(contexts)
        trace["candidates_total"] = len(candidates)
        if not candidates:
            return contexts, "no_ref_candidates", trace

        merged: dict[str, dict[str, Any]] = {}
        for c in contexts:
            merged[self._chunk_key(c.get("metadata", {}) or {})] = c

        followed: list[dict[str, Any]] = []
        for cand in candidates:
            follow, priority, why = self._should_follow_candidate_without_ref_content(
                query=query,
                targets=targets,
                candidate=cand,
            )
            row = {
                "ref_key": f"{cand.get('law_id', '')}:{cand.get('article', '') or '__law__'}",
                "follow": follow,
                "priority": priority,
                "reason": why,
            }
            trace["follow_checks"].append(row)
            if follow:
                cand2 = dict(cand)
                cand2["priority"] = priority
                followed.append(cand2)

        trace["candidates_followed"] = len(followed)
        if not followed:
            return contexts, "no_followed_ref_candidates", trace

        followed.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)
        used = 0
        for cand in followed:
            if used >= max_ref_expand:
                break
            law_id = str(cand.get("law_id", "")).zfill(6)
            article = str(cand.get("article", "")).strip()

            docs: list[dict[str, Any]] = []
            if article:
                docs = self.retriever.get_by_exact(law_id=law_id, article_num=article)
            else:
                # 법 전체 ref이면 해당 법 내부에서 query+target 기반으로만 부분 검색
                docs = self._retrieve_related_chunks_in_law(query=query, targets=targets, law_id=law_id, k=2)

            if not docs:
                continue

            for d in docs:
                key = self._chunk_key(d.get("metadata", {}) or {})
                if key not in merged:
                    merged[key] = d
            used += 1

        trace["expanded_ref_count"] = used
        return list(merged.values()), f"expanded_ref_count={used}", trace

    def _build_answer(self, query: str, targets: list[str], refs: list[dict[str, Any]]) -> str:
        evidence = []
        for r in refs[:5]:
            evidence.append(
                {
                    "law": r.get("law_name"),
                    "section": r.get("section"),
                    "excerpt": self._normalize_text(r.get("full_text", ""))[:420],
                }
            )

        appendix_terms = self.appendix.lookup(" ".join(targets), top_k=3)
        appendix_short = [
            {
                "category": t.get("category"),
                "subcategory": t.get("subcategory"),
                "description": str(t.get("description", ""))[:120],
            }
            for t in appendix_terms
        ]

        if self.llm is None:
            grounds = "\n".join([f"- {e['law']} {e['section']}" for e in evidence])
            return (
                f"질문: {query}\n"
                f"추출 타깃: {', '.join(targets)}\n"
                f"0-hop 근거 조항:\n{grounds}\n"
                "답변: 상기 조항을 기준으로 검토가 필요합니다."
            )

        prompt = (
            "너는 건축법률 QA 시스템의 0-hop 답변 생성기다.\n"
            "주의: 참조 추적(hop) 없이 현재 근거만으로 답한다.\n"
            "근거에 없는 수치/조건은 추정하지 말고 '근거 불충분'이라고 써라.\n"
            "출력 형식:\n"
            "1) 질문 요약\n2) 적용 근거\n3) 판단\n4) 추가 필요조건\n\n"
            f"query: {query}\n"
            f"targets: {targets}\n"
            f"appendix_terms: {appendix_short}\n"
            f"evidence: {evidence}\n"
        )
        response = self.llm.invoke(prompt)
        return getattr(response, "content", str(response))

    def ask(self, query: str, k: int = 5) -> ZeroHopResult:
        steps = [
            "질문을 분류하고 있습니다...",
            "0-hop 관련 문서를 찾고 있습니다...",
            "현재 근거만으로 답변 가능한지 판단하고 있습니다...",
            "필요한 경우에만 참조 법령/조항을 확장하고 있습니다...",
            "관련 법/조항을 정리하고 있습니다...",
            "최종 답변을 생성하고 있습니다...",
        ]
        targets = self.extract_targets(query)
        base_contexts = self.retrieve_zero_hop(query=query, targets=targets, k=k)
        contexts, expand_reason, trace = self._expand_refs_if_needed(
            query=query,
            targets=targets,
            contexts=base_contexts,
        )
        refs = self._build_references(contexts)
        answer = self._build_answer(query=query, targets=targets, refs=refs)
        trace["expand_reason"] = expand_reason
        trace["base_contexts_count"] = len(base_contexts)
        trace["final_contexts_count"] = len(contexts)

        return ZeroHopResult(
            answer=answer,
            targets=targets,
            steps=steps,
            references=refs,
            contexts_count=len(contexts),
            trace=trace,
        )
