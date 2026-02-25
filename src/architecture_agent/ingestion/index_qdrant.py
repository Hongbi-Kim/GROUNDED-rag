from __future__ import annotations

import os
from typing import Iterable

from architecture_agent.schemas import ArticleChunk


def _import_qdrant_stack():
    from langchain_core.documents import Document
    from langchain_naver import ClovaXEmbeddings
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams

    return Document, ClovaXEmbeddings, QdrantVectorStore, QdrantClient, Distance, VectorParams


def index_chunks_to_qdrant(
    chunks: Iterable[ArticleChunk],
    collection_name: str = "building_law",
    qdrant_path: str = "./qdrant_data",
    qdrant_url: str | None = None,
    qdrant_api_key: str | None = None,
    prefer_grpc: bool = False,
):
    Document, ClovaXEmbeddings, QdrantVectorStore, QdrantClient, Distance, VectorParams = _import_qdrant_stack()

    url = qdrant_url or os.getenv("QDRANT_URL")
    api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
    if url:
        client = QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc)
    else:
        client = QdrantClient(path=qdrant_path)
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    embeddings = ClovaXEmbeddings(model="bge-m3")
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )

    documents = []
    ids = []
    for chunk in chunks:
        documents.append(
            Document(
                page_content=chunk.content_resolved or chunk.content,
                metadata=chunk.to_payload(),
            )
        )
        ids.append(f"{chunk.law_id}:{chunk.article_num}")

    vector_store.add_documents(documents=documents, ids=ids)
    return vector_store
