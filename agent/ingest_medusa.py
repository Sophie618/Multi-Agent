"""
从 Medusa 拉取产品数据，chunk & embed 并写入 Chroma。
运行前请确认 MEDUSA_API_URL 与 API_KEY（如果需要）设置正确。
"""
import os
import httpx
from indexer_chroma import get_or_create_collection, upsert_documents
from embeddings import chunk_text
from dotenv import load_dotenv

load_dotenv()

MEDUSA_API_URL = os.getenv("MEDUSA_API_URL", "http://localhost:9000")
API_KEY = os.getenv("MEDUSA_PUBLISHABLE_KEY", "")  # optional

def get_headers():
    h = {}
    if API_KEY and "pk_" in API_KEY:
        h["x-publishable-api-key"] = API_KEY
    return h

async def fetch_products():
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{MEDUSA_API_URL}/store/products", headers=get_headers(), params={"limit": 250})
        resp.raise_for_status()
        data = resp.json()
        return data.get("products", [])

def product_to_chunks(prod: dict):
    """
    将单个 product 转为若干 chunk，并返回 chunks 与其对应的 metadata 列表
    metadata 包含 product_id, title, category, handle 等，便于后续过滤
    """
    title = prod.get("title", "")
    description = prod.get("description", "") or ""
    extras = []
    # include variant titles, options, tags if any
    variants = prod.get("variants", [])
    variant_texts = []
    for v in variants:
        variant_texts.append(v.get("title", ""))
        # sometimes variant has region specific prices, include price meta in chunk text
        prices = v.get("prices", [])
        if prices:
            # include first price as readable
            p = prices[0]
            amount = p.get("amount")
            currency = p.get("currency_code", "")
            if amount is not None:
                extras.append(f"价格: {amount/100} {currency}".strip())

    text = " ".join([title, description, " ".join(variant_texts), " ".join(extras)])
    chunks = chunk_text(text, chunk_size_words=200, overlap_words=40)
    metadatas = []
    for ch in chunks:
        meta = {
            "product_id": prod.get("id"),
            "title": title,
            "handle": prod.get("handle"),
            "category": prod.get("collection_id") or prod.get("category_id"),
            "source": "medusa",
        }
        metadatas.append(meta)
    return chunks, metadatas

async def ingest_all():
    col = get_or_create_collection()
    products = await fetch_products()
    all_docs = []
    all_metas = []
    for p in products:
        docs, metas = product_to_chunks(p)
        all_docs.extend(docs)
        all_metas.extend(metas)
    if all_docs:
        upsert_documents(col, all_docs, all_metas)
        print(f"Ingested {len(all_docs)} chunks from {len(products)} products.")
    else:
        print("No docs to ingest.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(ingest_all())