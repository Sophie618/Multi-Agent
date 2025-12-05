import asyncio
import os
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

SERVER_SCRIPT_PATH = "D:\\Multi_Agent\\agent\\agent_server.py"

async def run_agent_loop(user_query: str):
    print(f"👤 用户: {user_query}")
    
    server_params = StdioServerParameters(
        command="python", 
        args=[SERVER_SCRIPT_PATH],
        env=None
    )

    async with AsyncExitStack() as stack:
        # 启动连接
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        # 获取工具
        tools_result = await session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in tools_result.tools]
        
        print(f"🔧 Agent 已加载工具: {[t['name'] for t in available_tools]}")

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # 初始化对话历史
        messages = [{"role": "user", "content": user_query}]

        print("🤖 Agent 开始思考...")

        # 🔄 核心循环：支持多步行动
        while True:
            # 调用 LLM
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                tools=available_tools,
                messages=messages
            )

            # 把 LLM 的回复（可能是思考，也可能是工具调用请求）加入历史
            messages.append({"role": "assistant", "content": response.content})

            # 判断 LLM 是否想调用工具
            if response.stop_reason == "tool_use":
                # 找到它想调用的那个工具块
                tool_use = next(block for block in response.content if block.type == "tool_use")
                tool_name = tool_use.name
                tool_args = tool_use.input
                
                print(f"👉 LLM 决定调用工具: {tool_name} | 参数: {tool_args}")
                
                # 执行工具
                result = await session.call_tool(tool_name, tool_args)
                tool_output = result.content[0].text
                
                print(f"📦 工具返回结果: {tool_output[:100]}...") # 只打印前100个字避免刷屏

                # 把工具结果作为 User 视角的 tool_result 加入历史
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": tool_output
                        }
                    ]
                })
                # 循环继续，LLM 会看到工具结果，然后决定是继续调用下一个工具，还是回答问题
            else:
                # 如果没有调用工具，说明它生成了最终回复，打印并退出循环
                final_text = response.content[0].text
                print(f"\n🤖 Agent 最终回复:\n{final_text}")
                break

if __name__ == "__main__":
    question = "帮我查一下 Sweatshirt 的价格，然后告诉我它的详细材质。"
    asyncio.run(run_agent_loop(question))