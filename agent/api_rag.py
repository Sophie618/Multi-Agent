#把 RAG 整合到现有 FastAPI（这是把 RAG 做为一个可调用端点的示例）

from fastapi import FastAPI
from pydantic import BaseModel
from indexer_chroma import create_collection
from retriever import embed_query, retrieve
from rag_agent_tools import build_rag_prompt, ask_llm
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
col = create_collection()

class QueryReq(BaseModel):
    query: str

# 你需要实现 llm_client(prompt) 来调用你的 LLM（Anthropic/OpenAI）。这里只放一个伪实现。
# llm_client_stub 只是占位，实际要把 prompt 发给 Claude/OpenAI/Local LLM（Anthropic 的 API 还可以，但需要你封装请求并解析返回）。关键点：让 LLM 输出 JSON（用明确指令、schema、示例 few-shot）。
def llm_client_stub(prompt: str):
    # For prototyping, return a JSON instructing to call search_products:
    return '{"action":"search_products","params":{"query":"Sweatshirt"}}'

@app.post("/rag_query")
async def rag_query(q: QueryReq):
    # 1. retrieve top docs for context
    q_emb = embed_query(q.query)
    res = col.query(query_embeddings=[q_emb], n_results=3)
    docs = res['documents'][0] if 'documents' in res else []

    prompt = build_rag_prompt(q.query, docs)
    kind, payload = ask_llm(prompt, llm_client_stub)
    if kind == "tool":
        # Example: route to actual MCP tools or local functions
        action = payload.action
        params = payload.params
        return {"tool": action, "params": params}
    else:
        return {"answer": payload}