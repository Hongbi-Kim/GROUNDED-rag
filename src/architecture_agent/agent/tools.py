from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

try:
    from langchain_core.tools import tool
except Exception:  # pragma: no cover
    def tool(func=None, **_kwargs):
        if func is None:
            return lambda f: f
        return func


class Appendix1Index:
    def __init__(self, json_path: str = "data/processed/appendix1_terms.json"):
        self.json_path = Path(json_path)
        if not self.json_path.exists():
            raise FileNotFoundError(f"Appendix1 JSON not found: {self.json_path}")
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self.terms = data.get("terms", [])

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {t for t in re.split(r"[^0-9A-Za-z가-힣]+", text.lower()) if t}

    def lookup(self, term_or_query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query = term_or_query.strip()
        if not query:
            return []

        q_lower = query.lower()

        exact = []
        alias = []
        fuzzy = []
        q_tokens = self._tokenize(query)

        for term in self.terms:
            category = str(term.get("category", ""))
            subcategory = str(term.get("subcategory", ""))
            aliases = [str(a) for a in term.get("aliases", [])]
            desc = str(term.get("description", ""))

            if q_lower in category.lower() or q_lower in subcategory.lower():
                exact.append(term)
                continue

            if any(q_lower in a.lower() or a.lower() in q_lower for a in aliases):
                alias.append(term)
                continue

            doc_tokens = self._tokenize(" ".join([category, subcategory, " ".join(aliases), desc]))
            if not doc_tokens:
                continue
            score = len(q_tokens & doc_tokens) / len(q_tokens | doc_tokens) if q_tokens else 0.0
            if score > 0:
                fuzzy.append((score, term))

        fuzzy.sort(key=lambda x: x[0], reverse=True)
        result = exact + alias + [t for _, t in fuzzy]

        deduped = []
        seen = set()
        for t in result:
            key = (t.get("category"), t.get("subcategory"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(t)
            if len(deduped) >= top_k:
                break

        return deduped


class LawRetriever:
    def __init__(
        self,
        collection_name: str = "building_law",
        qdrant_path: str = "./qdrant_data",
        qdrant_url: str | None = None,
        qdrant_api_key: str | None = None,
        prefer_grpc: bool = False,
    ):
        from langchain_naver import ClovaXEmbeddings
        from langchain_qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient

        url = qdrant_url or os.getenv("QDRANT_URL")
        api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        if url:
            client = QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc)
        else:
            client = QdrantClient(path=qdrant_path)
        embeddings = ClovaXEmbeddings(model="bge-m3")
        self.vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )
        self.client = client
        self.collection_name = collection_name

    def similarity_search(self, query: str, k: int = 6) -> list[dict]:
        docs = self.vector_store.similarity_search(query, k=k)
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]

    def get_by_exact(self, law_id: str, article_num: str) -> list[dict]:
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        result, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="law_id", match=MatchValue(value=str(law_id))),
                    FieldCondition(key="article_num", match=MatchValue(value=str(article_num))),
                ]
            ),
            limit=5,
            with_payload=True,
            with_vectors=False,
        )
        return [
            {
                "content": point.payload.get("content_original", ""),
                "metadata": point.payload,
            }
            for point in result
        ]

    def find_children_by_parent_ref(self, law_name: str, article_num: str) -> list[dict]:
        result, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        out = []
        for point in result:
            payload = point.payload or {}
            refs = payload.get("parent_law_refs", [])
            for ref in refs:
                if ref.get("law_name") == law_name and str(ref.get("article")) == str(article_num):
                    out.append({"content": payload.get("content_original", ""), "metadata": payload})
                    break
        return out


def build_tools(
    retriever: LawRetriever,
    appendix_index: Appendix1Index,
):
    @tool
    def search_law_chunks(query: str, law_name: str | None = None, law_type: str | None = None, k: int = 6) -> list[dict]:
        """Semantic search for law chunks with optional metadata post-filtering."""
        items = retriever.similarity_search(query=query, k=max(k, 10))
        out = []
        for item in items:
            meta = item["metadata"]
            if law_name and meta.get("law_name") != law_name:
                continue
            if law_type and meta.get("law_type") != law_type:
                continue
            out.append(item)
            if len(out) >= k:
                break
        return out

    @tool
    def get_article(law_id: str, article_num: str) -> list[dict]:
        """Get exact article by law_id and article_num."""
        return retriever.get_by_exact(law_id=law_id, article_num=article_num)

    @tool
    def find_children_by_parent_ref(law_name: str, article_num: str) -> list[dict]:
        """Find 시행령 articles that reference parent law article."""
        return retriever.find_children_by_parent_ref(law_name=law_name, article_num=article_num)

    @tool
    def lookup_appendix1_term(term_or_query: str) -> list[dict]:
        """Lookup Appendix 1 taxonomy by exact, alias, and keyword matching."""
        return appendix_index.lookup(term_or_query=term_or_query)

    return [search_law_chunks, get_article, find_children_by_parent_ref, lookup_appendix1_term]
