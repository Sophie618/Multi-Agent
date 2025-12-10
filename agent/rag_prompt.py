"""
把检索到的 top_k 文档注入到 prompt 中，并返回一个 "instructional" prompt。
同时演示如何要求 LLM 返回 JSON 用于 function-calling。
"""
from typing import List, Dict
import json

def build_rag_prompt(user_query: str, docs: List[Dict], schema_example: dict = None):
    header = (
        "You are a factual shopping assistant. Use ONLY the provided DOCUMENTS to answer factual questions.\n"
        "If you need to call a tool (search_products / get_product_details / check_inventory), return a single JSON object matching the schema:\n"
        "{\"action\": <tool_name>, \"params\": { ... }}\n"
        "Return ONLY valid JSON when requesting a tool call. Do not add additional text.\n\n"
    )
    docs_text = "\n\n--- DOCUMENTS ---\n"
    for i, d in enumerate(docs):
        docs_text += f"[{i}] ({d['metadata'].get('product_id')}) {d['doc']}\n"
    schema_txt = ""
    if schema_example:
        schema_txt = "\n\nExample tool call JSON:\n" + json.dumps(schema_example, ensure_ascii=False, indent=2) + "\n"
    prompt = header + docs_text + schema_txt + "\nUser: " + user_query + "\nAssistant:"
    return prompt