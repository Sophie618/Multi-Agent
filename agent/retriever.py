#通过 Chroma 检索并做简单重排

"""
简单的 Retriever 封装：给一个文本 query，返回 top_k 文档和 metadata。
"""
from indexer_chroma import get_or_create_collection
from embeddings import model
import numpy as np

def embed_query_text(q: str):
    # reuse sentence-transformers model from embeddings.py
    emb = model.encode([q], normalize_embeddings=True).tolist()[0]
    return emb

def retrieve(query: str, top_k: int = 5, filter: dict = None):
    col = get_or_create_collection()
    q_emb = embed_query_text(query)
    # chroma supports where filter dict for metadata
    if filter:
        res = col.query(query_embeddings=[q_emb], n_results=top_k, where=filter)
    else:
        res = col.query(query_embeddings=[q_emb], n_results=top_k)
    # res contains documents, metadatas, distances
    docs = res.get("documents", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]
    distances = res.get("distances", [[]])[0]
    out = []
    for d, m, dist in zip(docs, metadatas, distances):
        out.append({"doc": d, "metadata": m, "distance": dist})
    return out