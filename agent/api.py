from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import json
from contextlib import AsyncExitStack

# 1. 导入通用客户端 (OpenAI标准)
from openai import OpenAI 

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT_PATH = os.path.join(BASE_DIR, "agent_server.py")

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_query = request.query
    print(f"🌐 收到前端请求: {user_query}")

    try:
        # 2. 初始化 DeepSeek 客户端
        # base_url 填 DeepSeek 的地址，如果是其他模型(如Moonshot)就换这个地址，代码不用动
        llm_client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), 
            base_url="https://api.deepseek.com"
        )

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[SERVER_SCRIPT_PATH],
            # 记得我们要解决 Windows 编码问题和环境变量问题
            env={**os.environ.copy(), "PYTHONUTF8": "1"}
        )

        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            # 获取工具列表
            tools_result = await session.list_tools()
            
            # 3. 转换工具格式 (OpenAI 格式 vs Anthropic 格式略有不同)
            openai_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema # MCP 的 schema 通常兼容 JSON Schema
                }
            } for t in tools_result.tools]

            print(f"🛠️ 发送给模型的工具: {json.dumps(openai_tools, indent=2, ensure_ascii=False)}")#调试代码，看看返回什么样子的工具

            # 初始化对话历史
            messages = [
                {"role": "system", "content": """
                你是一个拥有“查询商品数据库”能力的智能电商助手。
                你的任务是帮助用户查找商品。

                【重要规则】
                1. 当用户询问商品（如鼠标、T恤、价格、库存）时，你 **必须** 调用工具 `search_products` 获取真实数据。
                2. **绝对不要** 凭空捏造数据，也不要拒绝用户。
                3. 如果工具返回了数据，请根据数据回答；如果没返回，再告诉用户没找到。
                    """},
                {"role": "user", "content": user_query}
            ]
            
            final_reply = ""

            # 循环思考 (ReAct Loop)
            for _ in range(5):
                print("🤖 模型正在思考...")
                response = llm_client.chat.completions.create(
                    model="deepseek-chat", # 这里填 deepseek-chat
                    messages=messages,
                    tools=openai_tools,
                    temperature=0.0
                )

                response_message = response.choices[0].message
                
                # 4. 判断模型是否想调工具
                tool_calls = response_message.tool_calls

                if tool_calls:
                    # 把模型的“想调工具”的决定加入历史，防止它失忆
                    messages.append(response_message)

                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        # DeepSeek 返回的参数是字符串，需要解析
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        print(f"⚙️ 调用工具: {tool_name} | 参数: {tool_args}")
                        
                        # 执行 MCP 工具
                        result = await session.call_tool(tool_name, tool_args)
                        
                        # 获取结果文本
                        tool_output = result.content[0].text
                        print(f"✅ 工具返回: {tool_output[:50]}...")

                        # 5. 把工具结果喂回给模型
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_output
                        })
                else:
                    # 如果没有调工具，说明它生成了最终回答
                    final_reply = response_message.content
                    print(f"📢 最终回答: {final_reply}")
                    break
            
            return {"reply": final_reply}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)