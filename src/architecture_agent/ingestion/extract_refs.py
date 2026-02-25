from __future__ import annotations

import re

from architecture_agent.schemas import ArticleChunk, Reference

INTERNAL_PATTERN = re.compile(r"제(\d+(?:의\d+)?)조(?:제(\d+)항)?(?:제(\d+)호)?(?:제([가-힣A-Za-z0-9]+)목)?")
EXTERNAL_PATTERN = re.compile(r"「([^」]+)」\s*제(\d+(?:의\d+)?)조(?:\s*제(\d+)항)?(?:\s*제(\d+)호)?")
PARENT_PATTERN = re.compile(r"(?<![가-힣])법\s*제(\d+(?:의\d+)?)조(?:제(\d+)항)?(?:제(\d+)호)?")


def _dedupe_refs(refs: list[Reference]) -> list[Reference]:
    seen = set()
    out = []
    for ref in refs:
        key = (ref.ref_type, ref.law_name, ref.article, ref.paragraph, ref.item)
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
    return out


def extract_references(chunks: list[ArticleChunk]) -> None:
    for chunk in chunks:
        text = chunk.content

        external_refs: list[Reference] = []
        for m in EXTERNAL_PATTERN.finditer(text):
            ref_law = m.group(1).strip()
            if ref_law == chunk.law_name:
                continue
            external_refs.append(
                Reference(
                    ref_type="external",
                    law_name=ref_law,
                    article=m.group(2),
                    paragraph=m.group(3),
                    item=m.group(4),
                    raw=m.group(0),
                )
            )

        text_without_external = EXTERNAL_PATTERN.sub("", text)

        internal_refs: list[Reference] = []
        for m in INTERNAL_PATTERN.finditer(text_without_external):
            internal_refs.append(
                Reference(
                    ref_type="internal",
                    law_name=chunk.law_name,
                    article=m.group(1),
                    paragraph=m.group(2),
                    item=m.group(3) or m.group(4),
                    raw=m.group(0),
                )
            )

        parent_refs: list[Reference] = []
        if chunk.law_type == "시행령":
            for m in PARENT_PATTERN.finditer(text):
                parent_refs.append(
                    Reference(
                        ref_type="parent",
                        law_name="건축법",
                        article=m.group(1),
                        paragraph=m.group(2),
                        item=m.group(3),
                        raw=m.group(0),
                    )
                )

        chunk.external_refs = _dedupe_refs(external_refs)
        chunk.internal_refs = _dedupe_refs(internal_refs)
        chunk.parent_law_refs = _dedupe_refs(parent_refs)
