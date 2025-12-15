# Multi-Agent E-commerce Assistant

这是一个基于 **Model Context Protocol (MCP)** 构建的多智能体电商助手项目。它结合了 **Vue 3** 前端、**FastAPI** 中间层、**Anthropic Claude** 大模型以及 **Medusa** 电商后端，实现了一个能够查询商品库存、获取商品详情的智能对话系统。

## 🏗️ 架构概览

本项目采用典型的分层架构，通过 MCP 协议连接 LLM 与本地工具。

![Architecture Diagram](architecture_diagram.png)

### 核心组件

1.  **Frontend (Vue 3)**: 用户交互界面，负责发送聊天请求并展示回复。
2.  **API Gateway (FastAPI)**: 
    *   作为系统的入口，接收前端请求。
    *   充当 **MCP Client**，负责启动和管理 MCP Server 子进程。
    *   负责与 **Anthropic Claude API** 进行交互，处理 Tool Use 逻辑。
3.  **MCP Server (FastMCP)**:
    *   实现了具体的工具逻辑（如 `search_products`, `get_product_details`）。
    *   通过 HTTP 请求与 **Medusa Backend** 进行通信。
4.  **Medusa Backend**: 开源无头电商引擎，提供商品数据和业务逻辑支持。

### 交互流程

1.  **用户提问**: 用户在 Vue 前端输入问题（例如：“帮我查下T恤库存”）。
2.  **请求转发**: 前端发送 POST 请求到 `api.py`。
3.  **工具发现**: `api.py` 启动 `agent_server.py`，获取可用工具列表。
4.  **LLM 决策**: `api.py` 将用户问题和工具描述发送给 Claude，Claude 决定调用 `search_products` 工具。
5.  **工具执行**: `api.py` 通过 MCP 协议（Stdio）请求 `agent_server.py` 执行工具。
6.  **数据获取**: `agent_server.py` 调用 Medusa API 获取真实商品数据。
7.  **生成回复**: 结果返回给 Claude，Claude 生成自然语言回复，最终展示给用户。

## 📂 目录结构

```
Multi_Agent/
├── agent/                  # Python 后端与 Agent 实现
│   ├── agent_server.py     # MCP Server：定义工具与 Medusa 交互
│   ├── api.py              # FastAPI 应用：MCP Client 与 LLM 交互
│   ├── agent_client.py     # (可选) 独立的 MCP Client 测试脚本
│   └── ...
├── frontend/               # Vue 3 前端项目
│   ├── src/
│   ├── package.json
│   └── ...
├── medusa-backend/         # Medusa 电商后端
│   ├── src/
│   ├── medusa-config.ts
│   └── ...
└── environment.yml         # Python 环境依赖
```

## 🚀 快速开始

### 前置要求

*   Python 3.10+
*   Node.js & npm
*   Medusa 后端已启动并运行在 `http://localhost:9000`
*   Anthropic API Key

### 1. 配置环境变量

在 `agent/` 目录下创建 `.env` 文件：

```env
ANTHROPIC_API_KEY=sk-ant-...
MEDUSA_API_KEY=pk_... (可选，视 Medusa 配置而定)
```

### 2. 启动 Medusa 后端

请参考 `medusa-backend/README.md` 启动 Medusa 服务。通常命令为：

```bash
cd medusa-backend
npm run dev
```

### 3. 启动 Agent API 服务

```bash
cd agent
# 建议使用 conda 或 venv 环境
pip install -r requirements.txt  # 需自行生成或安装依赖 (fastapi, uvicorn, mcp, anthropic, httpx, python-dotenv)
python api.py
```
服务将在 `http://localhost:8000` 启动。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```
访问前端页面（通常是 `http://localhost:5173`），即可开始对话。

## 🛠️ 技术栈

*   **Model Context Protocol (MCP)**: 用于连接 AI 模型与本地工具的标准协议。
*   **FastAPI**: 高性能 Python Web 框架。
*   **Anthropic Claude 3.5 Sonnet**: 强大的推理模型，支持 Tool Use。
*   **Medusa.js**: 灵活的开源无头电商平台。
*   **Vue.js**: 渐进式 JavaScript 框架。

## 📝 功能列表

*   [x] **商品搜索**: 支持模糊搜索商品名称。
*   [x] **价格查询**: 自动解析 Medusa 复杂的价格结构并展示。
*   [x] **商品详情**: 获取商品的材质、描述及变体信息。
*   [ ] **RAG 支持**: (开发中) 基于向量数据库的文档检索。
