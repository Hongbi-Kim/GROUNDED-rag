from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from architecture_agent.service.zero_hop import ZeroHopLawAgent


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(default=5, ge=1, le=15)


class AskResponse(BaseModel):
    answer: str
    targets: list[str]
    steps: list[str]
    references: list[dict]
    contexts_count: int
    trace: dict


@lru_cache(maxsize=1)
def get_agent() -> ZeroHopLawAgent:
    return ZeroHopLawAgent(
        collection_name=os.getenv("QDRANT_COLLECTION", "building_law"),
        qdrant_path=os.getenv("QDRANT_PATH", "./qdrant_data"),
        qdrant_url=os.getenv("QDRANT_URL") or None,
        qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
        qdrant_prefer_grpc=(os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true"),
        appendix_json=os.getenv("APPENDIX_JSON", "data/processed/appendix1_terms.json"),
        answer_model=os.getenv("CLOVA_MODEL", "HCX-005"),
        answer_temperature=float(os.getenv("CLOVA_TEMPERATURE", "0.0")),
    )


app = FastAPI(title="Architecture Law Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/chat/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        result = get_agent().ask(query=req.query.strip(), k=req.k)
        return AskResponse(
            answer=result.answer,
            targets=result.targets,
            steps=result.steps,
            references=result.references,
            contexts_count=result.contexts_count,
            trace=result.trace,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ask failed: {exc}") from exc
