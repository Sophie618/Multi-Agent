from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import sys
from contextlib import AsyncExitStack

# 复用我们之前的 Client 代码逻辑
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 允许 Vue 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVER_SCRIPT_PATH = "D:\\Multi_Agent\\agent\\agent_server.py"

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    接收前端发来的问题，运行 Agent 循环，返回最终答案。
    """
    user_query = request.query
    print(f"🌐 收到前端请求: {user_query}")

    try:
        # --- 这里就是 agent_client.py 的核心逻辑 ---
        server_params = StdioServerParameters(
            command="python", 
            args=[SERVER_SCRIPT_PATH],
            env=None
        )

        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            tools_result = await session.list_tools()
            available_tools = [{
                "name": t.name, 
                "description": t.description, 
                "input_schema": t.inputSchema
            } for t in tools_result.tools]

            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            messages = [{"role": "user", "content": user_query}]
            
            final_reply = ""

            # 最多循环 5 次，防止死循环
            for _ in range(5):
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    tools=available_tools,
                    messages=messages
                )
                
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "tool_use":
                    tool_use = next(b for b in response.content if b.type == "tool_use")
                    tool_name = tool_use.name
                    tool_args = tool_use.input
                    
                    print(f"⚙️ 调用工具: {tool_name}")
                    
                    result = await session.call_tool(tool_name, tool_args)
                    tool_output = result.content[0].text
                    
                    messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": tool_output}]
                    })
                else:
                    final_reply = response.content[0].text
                    break
            
            return {"reply": final_reply}

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 在 8000 端口启动 API 服务
    uvicorn.run(app, host="0.0.0.0", port=8000)