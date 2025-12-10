#把数据写入 Chroma向量数据库

import chromadb
from chromadb.config import Settings
from typing import List, Dict
import uuid
from embeddings import embed_texts

# 本地持久化 Chroma（duckdb + parquet）
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma_db"))

def get_or_create_collection(name: str = "smartshopper"):
    return client.get_or_create_collection(name)

def upsert_documents(collection, docs: List[str], metadatas: List[Dict]):
    """
    docs: list of strings (chunks)
    metadatas: list of dicts (must be same length as docs)
    """
    ids = [str(uuid.uuid4()) for _ in docs]
    embeddings = embed_texts(docs)
    collection.add(documents=docs, metadatas=metadatas, ids=ids, embeddings=embeddings)
    # 持久化
    client.persist()