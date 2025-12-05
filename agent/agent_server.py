# agent_server.py
from mcp.server.fastmcp import FastMCP#用来快速创建Model Context Protocol服务器的工具
import httpx#导入httpx库，用于发送HTTP异步请求
import asyncio#导入asyncio库，用于异步编程
import json

# 🔴 这里填入你刚才在后台复制的 Publishable API Key (pk_...)
# 如果你找不到 Key，先留空试试，但 Medusa 2.0 通常需要它
API_KEY="pk_c6797ee981d3a56db47ecb9c3144e0f1ad7c0e56a2559299be21668a08299c5e"# Medusa的公开API密钥

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
    搜索商城里的商品。
    """
    # 改用 stderr 打印日志，防止破坏 MCP 协议
    import sys
    print(f"[Search] Searching for: {query}", file=sys.stderr)
    
    try:
        async with httpx.AsyncClient() as client:
            # 基础参数，不加 currency_code 防止报错
            params = {"q": query, "limit": 3} 
            
            response = await client.get(
                f"{MEDUSA_API_URL}/store/products", 
                headers=get_headers(),
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                
                if not products:
                     return "查询成功，但没有找到任何商品。"

                found = []
                debug_info = "" # 用于存储第一条数据的调试信息

                for index, p in enumerate(products):
                    title = p.get('title', '未知商品')
                    p_id = p.get('id', '')
                    
                    # --- 价格提取逻辑 ---
                    price_str = "价格暂无"
                    variants = p.get('variants', [])
                    
                    # 🔴 强制抓取调试信息：如果是第一个商品，把它的 variants 数据抓出来
                    if index == 0 and variants:
                        # 只取前 500 个字符防止刷屏
                        raw_dump = json.dumps(variants[0], indent=2)[:500]
                        debug_info = f"\n\n🔍 [DEBUG DATA]:\n{raw_dump}\n"

                    if variants:
                        prices = variants[0].get('prices', [])
                        if prices:
                            # 尝试直接读取 amount
                            amount = prices[0].get('amount')
                            currency = prices[0].get('currency_code', 'usd').upper()
                            if amount is not None:
                                price_str = f"{amount / 100} {currency}"
                    
                    found.append(f"- {title} (ID: {p_id}) | 价格: {price_str}")
                
                # 结果中包含 Debug 信息，这样 Client 一定能看见
                return "找到以下商品:\n" + "\n".join(found) + debug_info
            else:
                return f"搜索失败 (状态码 {response.status_code}): {response.text}"
    except Exception as e:
        return f"发生异常: {str(e)}"

@mcp.tool()
async def get_product_details(product_id: str) -> str:
    """
    获取特定商品的详细信息。
    """
    import sys
    print(f"[Details] Getting details for ID: {product_id}", file=sys.stderr)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEDUSA_API_URL}/store/products/{product_id}",
                headers=get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                product = data.get('product', {})
                
                title = product.get('title', '未知')
                desc = product.get('description', '无描述')
                material = product.get('material', '未填写')
                
                # 简单的变体信息
                variants_info = []
                if 'variants' in product:
                    for v in product['variants']:
                        v_title = v.get('title', '')
                        variants_info.append(v_title)

                info = (
                    f"商品名: {title}\n"
                    f"描述: {desc}\n"
                    f"材质: {material}\n"
                    f"可选规格: {', '.join(variants_info)}\n"
                )
                return info
            else:
                return f"查询详情失败: {response.status_code}"
                
    except Exception as e:
        return f"查询详情异常: {str(e)}"

if __name__ == "__main__":
    mcp.run()