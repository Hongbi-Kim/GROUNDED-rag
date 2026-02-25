from __future__ import annotations

import json
from pathlib import Path

from architecture_agent.ingestion.build_appendix1_json import build_appendix1_json
from architecture_agent.ingestion.extract_refs import extract_references
from architecture_agent.ingestion.fetch_law import DEFAULT_LAW_IDS, fetch_and_save_laws
from architecture_agent.ingestion.index_qdrant import index_chunks_to_qdrant
from architecture_agent.ingestion.parse_law import parse_law_data
from architecture_agent.ingestion.resolve_abbr import (
    extract_abbreviations_by_law,
    resolve_abbreviations,
    resolve_abbreviations_by_chunk,
    save_abbreviation_maps_by_chunk,
    save_abbreviation_maps_by_law,
)


def run_ingestion(
    law_ids: tuple[str, ...] = DEFAULT_LAW_IDS,
    raw_dir: str = "data/processed/raw",
    abbr_mode: str = "llm_chunk",
    abbr_maps_path: str = "data/processed/abbr_maps_by_law.json",
    abbr_chunk_maps_path: str = "data/processed/abbr_maps_by_chunk.json",
    llm_model_for_abbr: str = "HCX-005",
    collection_name: str = "building_law",
    qdrant_path: str = "./qdrant_data",
    qdrant_url: str | None = None,
    qdrant_api_key: str | None = None,
    qdrant_prefer_grpc: bool = False,
) -> dict:
    raw_files = fetch_and_save_laws(law_ids=law_ids, output_dir=raw_dir)

    all_chunks = []
    for f in raw_files:
        payload = json.loads(Path(f).read_text(encoding="utf-8"))
        all_chunks.extend(parse_law_data(payload))

    extract_references(all_chunks)
    abbr_chunk_path = None

    if abbr_mode == "llm_chunk":
        from architecture_agent.ingestion.extract_abbr_chunk_llm import (
            aggregate_chunk_abbr_maps_by_law,
            extract_abbreviations_by_chunk_llm,
        )

        chunk_maps = extract_abbreviations_by_chunk_llm(
            all_chunks,
            model=llm_model_for_abbr,
        )
        resolve_abbreviations_by_chunk(all_chunks, chunk_maps)
        law_abbr_maps = aggregate_chunk_abbr_maps_by_law(all_chunks, chunk_maps)
        abbr_chunk_path = save_abbreviation_maps_by_chunk(
            chunk_maps,
            output_path=abbr_chunk_maps_path,
        )
    else:
        law_abbr_maps = extract_abbreviations_by_law(all_chunks)
        resolve_abbreviations(all_chunks, law_abbr_maps)

    abbr_path = save_abbreviation_maps_by_law(law_abbr_maps, output_path=abbr_maps_path)

    store = index_chunks_to_qdrant(
        chunks=all_chunks,
        collection_name=collection_name,
        qdrant_path=qdrant_path,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        prefer_grpc=qdrant_prefer_grpc,
    )

    appendix_path = build_appendix1_json()

    return {
        "raw_files": [str(p) for p in raw_files],
        "abbr_mode": abbr_mode,
        "abbr_maps_json": str(abbr_path),
        "abbr_chunk_maps_json": str(abbr_chunk_path) if abbr_chunk_path else "",
        "appendix_json": str(appendix_path),
        "chunks": len(all_chunks),
        "abbreviations_total": sum(len(v) for v in law_abbr_maps.values()),
        "abbreviations_by_law": {k: len(v) for k, v in law_abbr_maps.items()},
        "collection": collection_name,
        "vector_store": str(type(store)),
    }


if __name__ == "__main__":
    result = run_ingestion()
    for k, v in result.items():
        print(f"{k}: {v}")
