# agent_server.py
# 在 agent 的 MCP 工作流中也可以把 RAG-built prompt 作为工具的内部来源（即当 Agent 决定 search_products 时，Server 会先做检索，把检索结果一并返回给 Agent/LLM）。
from mcp.server.fastmcp import FastMCP#用来快速创建Model Context Protocol服务器的工具
import httpx#导入httpx库，用于发送HTTP异步请求
import asyncio#导入asyncio库，用于异步编程
import json#json库处理json数据
import os#导入os库，用于操作系统相关功能
from dotenv import load_dotenv#从.env文件加载环境变量

# 🔴 这里填入你刚才在后台复制的 Publishable API Key (pk_...)
# 如果你找不到 Key，先留空试试，但 Medusa 2.0 通常需要它
API_KEY=os.getenv("MEDUSA_API_KEY")# Medusa的公开API密钥

# 定义服务名称
mcp = FastMCP("My-Ecom-Agent")#创建名为"My-Ecom-Agent"的MCP服务器实例
# 这里的地址必须是你 Medusa 运行的地址
MEDUSA_API_URL = "http://localhost:9000"#指向本地运行的Medusa API服务器后续请求都会发往这个网址

def get_headers():
    headers = {}
    # 简单的防御性编程，防止 Key 是空的
    if API_KEY and "pk_" in API_KEY:
        headers["x-publishable-api-key"] = API_KEY
    return headers

@mcp.tool()
async def search_products(query: str) -> str:
    """
    搜索商城里的商品。返回商品列表、ID和价格。
    如果用户问“有什么T恤”，就用这个。
    """
    print(f"🔍 正在搜索: {query} ...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Medusa 2.0 的搜索参数通常是 q
            params = {"q": query, "limit": 5} 
            
            response = await client.get(
                f"{MEDUSA_API_URL}/store/products", 
                headers=get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                
                if not products:
                     return "查询成功，但没有找到任何匹配的商品。"

                found = []
                for p in products:
                    title = p.get('title', '未知商品')
                    p_id = p.get('id', '')
                    
                    # ✅ 任务一：修复价格显示
                    # Medusa 的价格结构很深: variants -> prices -> amount
                    price_str = "价格暂无"
                    variants = p.get('variants', [])
                    if variants:
                        # 取第一个变体的价格列表
                        prices = variants[0].get('prices', [])
                        # 这里的逻辑是：优先找 USD 或 EUR，或者直接取第一个
                        # 注意：Medusa 这里的 amount 通常是“分”，比如 1950 代表 19.50
                        if prices:
                            # 简单起见，直接取第一个价格
                            raw_amount = prices[0].get('amount', 0)
                            currency = prices[0].get('currency_code', 'usd').upper()
                            # 除以100转成元
                            final_price = raw_amount / 100
                            price_str = f"{final_price} {currency}"
                    
                    # 把 ID 也返回给 LLM，方便它下一步查询详情
                    found.append(f"- {title} (ID: {p_id}) | 价格: {price_str}")
                
                return "找到以下商品:\n" + "\n".join(found)
            else:
                print(f"Error Body: {response.text}") 
                return f"搜索失败 (状态码 {response.status_code})"
    except Exception as e:
        return f"发生异常: {str(e)}"

# ✅ 任务二：新增获取商品详情工具
@mcp.tool()
async def get_product_details(product_id: str) -> str:
    """
    获取特定商品的详细信息（材质、描述、所有变体等）。
    必须提供商品的 ID (例如: prod_01H...)。
    当用户问“这件衣服是什么材质”或“详细介绍一下”时使用。
    """
    print(f"📖 正在查询详情 ID: {product_id} ...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEDUSA_API_URL}/store/products/{product_id}",
                headers=get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                # 注意 Medusa get by ID 返回结构通常是 { "product": {...} }
                product = data.get('product', {})
                
                title = product.get('title', '未知')
                description = product.get('description', '暂无描述')
                material = product.get('material', '未知材质')
                
                # 整理变体信息（比如尺码、颜色）
                options_info = []
                if 'options' in product:
                    for opt in product['options']:
                        values = [v['value'] for v in opt.get('values', [])]
                        options_info.append(f"{opt['title']}: {', '.join(values)}")
                
                info = (
                    f"商品名: {title}\n"
                    f"描述: {description}\n"
                    f"材质: {material}\n"
                    f"可选规格: {' | '.join(options_info)}\n"
                )
                return info
            else:
                return f"查询详情失败: 找不到 ID 为 {product_id} 的商品"
                
    except Exception as e:
        return f"查询详情异常: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')#Server 启动后才会挂起，一直监听 Client发过来的指令