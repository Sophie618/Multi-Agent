import asyncio#异步编程用于运行async
import os
from contextlib import AsyncExitStack#上下文管理器，管理多个异步资源的打开和关闭
from mcp import ClientSession, StdioServerParameters#客户端会话和配置如何启动服务器进程
from mcp.client.stdio import stdio_client#最核心，用于通过标准输入输出与MCP服务器通信（弹出终端）
from anthropic import Anthropic#Claude官方SDK
from dotenv import load_dotenv#从.env文件加载环境变量

load_dotenv()#加载环境变量

# 获取当前文件所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 动态拼接路径，无论在谁的电脑上都能跑
SERVER_SCRIPT_PATH = os.path.join(BASE_DIR, "agent_server.py")

async def run_agent_loop(user_query: str):#定义异步函数接受用户的查询字符串
    print(f"👤 用户: {user_query}")#打印用户的问题
    
    server_params = StdioServerParameters(#启动mcp脚本的配置参数（其实就是模拟终端里面的命令行）
        command="python", #启动python将mcp脚本作为子进程运行
        args=[SERVER_SCRIPT_PATH],#相当于在终端里面去执行python agent/agent_server.py
        env=None
    )

    async with AsyncExitStack() as stack:#这句话就是只要退出此代码块按顺序把刚刚放入栈的东西全部关闭，不占内存
        # 启动连接
        read, write = await stack.enter_async_context(stdio_client(server_params))#启动子进程并建立通信管道，read输入流对象，对应子进程server的输出，write输出流对象对应子进程的输入
        session = await stack.enter_async_context(ClientSession(read, write))#创建mcp客户端会话
        await session.initialize()#执行MCP握手协议（其实就是初始化连接）
        
        # 获取工具
        tools_result = await session.list_tools()#询问服务器有哪些工具可用
        available_tools = [{#把工具信息转换为Claude能理解的格式：名称，描述，参数结构
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in tools_result.tools]
        
        print(f"🔧 Agent 已加载工具: {[t['name'] for t in available_tools]}")

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))#初始化Claude客户端实例，需要读取api_key
        
        # 初始化对话历史，放入用户的问题
        messages = [{"role": "user", "content": user_query}]

        print("🤖 Agent 开始思考...")

        # 🔄 核心循环：支持多步行动，ReAct模式：即先思考再行动的循环
        while True:
            # 调用 LLM
            response = client.messages.create(#调用LLM提供的参数
                model="claude-3-5-sonnet-20241022",#模型类型
                max_tokens=1024,#最大生成长度
                tools=available_tools,#提供可供使用的工具列表
                messages=messages#提供对话历史
            )

            # 把 LLM 的回复（可能是思考，也可能是工具调用请求）加入历史保持上下文连贯
            messages.append({"role": "assistant", "content": response.content})

            # 判断 LLM 是否想调用工具
            if response.stop_reason == "tool_use":#停止推理原因为llm决定调用工具
                # 找到它想调用的那个工具块
                tool_use = next(block for block in response.content if block.type == "tool_use")
                tool_name = tool_use.name#工具名
                tool_args = tool_use.input#工具参数
                
                print(f"👉 LLM 决定调用工具: {tool_name} | 参数: {tool_args}")
                
                # 执行工具
                result = await session.call_tool(tool_name, tool_args)#使用工具
                tool_output = result.content[0].text#获取工具返回的文本结果，content[0]没有开启“思维链 (Chain of Thought)”等高级功能的情况下，Claude 的普通文本回复通常也只包含一个文本块;如果是一个健壮的生产环境代码，不应该直接取 [0]，而是应该遍历列表。
                
                print(f"📦 工具返回结果: {tool_output[:100]}...") # 只打印前100个字避免刷屏

                # 把工具结果作为 User 视角的 tool_result 加入历史保持上下文连贯
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
            else:#stop_reason!=tool_use(通常=end_turn)
                # 如果没有调用工具，说明它生成了最终回复，打印并退出循环
                final_text = response.content[0].text
                print(f"\n🤖 Agent 最终回复:\n{final_text}")
                break

if __name__ == "__main__":
    question = "帮我查一下 Sweatshirt 的价格，然后告诉我它的详细材质。"
    asyncio.run(run_agent_loop(question))