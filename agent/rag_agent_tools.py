#把检索加入 prompt，要求 LLM 返回 JSON（并演示 function-calling 风格）

import os
import json
from retriever import embed_query, retrieve
from indexer_chroma import create_collection
from pydantic import BaseModel, ValidationError

# 一个用于校验 LLM 返回结构的 pydantic schema
class ActionSchema(BaseModel):
    action: str
    params: dict

# Build prompt that injects retrieved documents
def build_rag_prompt(user_query: str, docs: list):
    header = (
        "You are an AI shopping assistant. Use the provided DOCUMENTS as ground-truth. "
        "If the user asks for price, inventory or material, you must call a tool by emitting a JSON object "
        "matching the schema: {\"action\": <tool_name>, \"params\": {...}}. "
        "Available actions: search_products, get_product_details, check_inventory. "
        "Return ONLY a single JSON object when you call a tool.\n\n"
    )
    docs_text = "\n\n--- DOCUMENTS ---\n"
    for i, d in enumerate(docs):
        docs_text += f"[{i}] {d}\n"
    prompt = header + docs_text + f"\n\nUser: {user_query}\nAssistant:"
    return prompt

# Example function that "asks the LLM" — replace with your actual LLM client call
def ask_llm(prompt: str, llm_client):
    """
    llm_client should be a callable that returns text. Here we expect the LLM to either:
    - Return a JSON action to call a tool, e.g. {"action":"get_product_details","params":{"product_id":"prod_..."}}
    - Or return a final answer.
    """
    response_text = llm_client(prompt)
    # Try to parse JSON from text
    try:
        obj = json.loads(response_text.strip())
        validated = ActionSchema(**obj)
        return ("tool", validated)
    except (json.JSONDecodeError, ValidationError):
        return ("answer", response_text)