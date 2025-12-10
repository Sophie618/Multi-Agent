# 处理文本分块并生成 embeddings（使用 sentence-transformers）

from sentence_transformers import SentenceTransformer
from typing import List

# model: 小而快的 embedding 模型，适合 CPU（如果有GPU可以换 bigger model）
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)

def chunk_text(text: str, chunk_size_words: int = 200, overlap_words: int = 40) -> List[str]:
    """
    简单按单词分块（近似 token）。建议 chunk_size_words 设在 200-600 范围。
    """
    if not text:
        return []
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size_words])
        chunks.append(chunk)
        i += chunk_size_words - overlap_words
    return chunks

def embed_texts(texts: List[str]):
    """
    返回向量（list of lists）。在 CPU 上可能较慢，批量化会快一点。
    """
    if not texts:
        return []
    # model.encode 返回 numpy array
    embs = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    return embs.tolist()