# ContextOS

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-26%20passed-brightgreen)](tests/)

**Claude Context Operating System** — 面向 Claude API 的透明代理层，提供 Token 可观测、上下文控制、Session 管理和 Session Fork 能力。

[English](./README.md)

---

## 🎯 解决的问题

长时间运行的 Claude 对话面临以下问题：
- **上下文爆炸** — Token 用量无限制增长，触碰模型上限
- **缺乏可视性** — 无法追踪每次对话的 Token 消耗
- **历史记录丢失** — 重新开始对话会丢失有价值的上下文
- **任务中断** — 长任务在上下文窗口溢出时断裂

## ✨ 解决方案

ContextOS 位于你和 Claude API 之间，提供：

| 功能 | 收益 |
|------|------|
| **Token 可观测** | 实时 prompt/completion 拆分，图表可视化 |
| **Session 管理** | SQLite 持久化，对话不丢失 |
| **Session Fork** | 对话分支，父子血缘追踪 |
| **Context Engine** | 自动消息裁剪、工具裁剪、Skill 注入 |
| **Web Dashboard** | React 界面，React Flow 图谱 + Recharts 图表 |

---

## 📸 界面截图

### Sessions 列表

![Sessions Dashboard](docs/sessions-list.png)

### Fork 关系图谱

![Fork Graph](docs/fork-graph.png)

*Fork 图谱展示 Session 的父子血缘关系、Fork 点 Token 数，支持交互式导航。*

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（可选，用于前端构建）
- [Anthropic API Key](https://console.anthropic.com/settings/keys)

### 安装方式

#### 方式 A：虚拟环境（推荐）

```bash
git clone https://github.com/CRF2004/ContextOS.git
cd ContextOS

python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

pip install -e ".[dev]"
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199
```

#### 方式 B：pipx（最干净）

```bash
pipx install git+https://github.com/CRF2004/ContextOS.git
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199
```

#### 方式 C：不安装直接运行

```bash
git clone https://github.com/CRF2004/ContextOS.git
cd ContextOS
pip install fastapi uvicorn httpx aiosqlite pydantic python-dotenv tiktoken
PYTHONPATH=src ANTHROPIC_API_KEY=sk-ant-... python -m contextos.cli run --port 8199
```

### 构建前端（可选）

```bash
cd web
npm install
npm run build    # 输出到 ../dist/web
```

---

## 📖 使用方式

### CLI 命令

```bash
# 启动 Proxy 服务
contextos run --port 8199 --db ./contextos.db

# 列出所有 Session
contextos sessions

# 查看 Token 用量
contextos tokens sess_abc123

# 查看请求日志
contextos logs sess_abc123
```

### API 示例

#### 创建 Session

```bash
curl -X POST http://localhost:8199/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "my-conversation"}'
```

**响应：**
```json
{
  "session_id": "sess_a1b2c3d4e5f6",
  "name": "my-conversation",
  "status": "active",
  "parent_session_id": null,
  "total_tokens": 0,
  "created_at": "2026-05-04T12:00:00.000000+00:00"
}
```

#### 通过 Proxy 调用 Claude

```bash
curl -X POST "http://localhost:8199/api/proxy/messages?session_id=sess_a1b2c3d4e5f6" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

#### Fork Session

```bash
curl -X POST http://localhost:8199/api/sessions/sess_a1b2c3d4e5f6/fork \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_a1b2c3d4e5f6",
    "name": "my-conversation-branch",
    "carry_messages": 5
  }'
```

#### 获取 Fork 图谱

```bash
curl http://localhost:8199/api/sessions/sess_a1b2c3d4e5f6/fork-graph
```

---

## 🏗 架构设计

```
                 ┌──────────────────────┐
                 │   Web Dashboard       │
                 │  (React + TypeScript) │
                 └─────────┬────────────┘
                           │
                 ┌─────────▼────────────┐
                 │   FastAPI Server     │
                 │     (Port 8199)      │
                 ├─────────┬────────────┤
                 │         │            │
     ┌───────────▼───┐ ┌──▼──────────┐ ┌▼─────────────┐
     │ Context Engine │ │ Fork Engine │ │ Token Profiler│
     └───────────┬───┘ └────┬────────┘ └────┬─────────┘
                 │           │               │
                 └────┬──────┴──────┬──────┘
                      │             │
            ┌─────────▼─────────────▼─────────┐
            │        Proxy Layer              │
            │   (拦截 → 分析 → 记录)           │
            └────────────────────────────────┘
                      │
                 Claude API
```

### 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **Proxy** | `proxy.py` | 拦截请求、转发 Claude、捕获响应 |
| **Token Profiler** | `token_profiler.py` | 使用 tiktoken 计数（支持 Claude 模型） |
| **Session Store** | `session_store.py` | SQLite 持久化 Session/Token/Log |
| **Context Engine** | `context_engine.py` | 消息裁剪、工具裁剪、Skill 注入 |
| **Fork Engine** | `fork_engine.py` | 手动/自动 Fork（Token 阈值触发） |

---

## 📡 API 端点

### Sessions

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/sessions` | 创建 Session |
| `GET` | `/api/sessions` | 列出 Sessions |
| `GET` | `/api/sessions/{id}` | 获取 Session |
| `POST` | `/api/sessions/{id}/archive` | 归档 Session |

### Tokens

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/sessions/{id}/tokens` | Token 汇总 |
| `GET` | `/api/sessions/{id}/tokens/history` | Token 历史 |
| `POST` | `/api/tokens/count` | 文本 Token 计数 |

### Forks

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/sessions/{id}/fork` | Fork Session |
| `GET` | `/api/sessions/{id}/fork-graph` | 获取 Fork 图谱 |

### Proxy

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/proxy/messages?session_id=xxx` | 转发到 Claude |

---

## 🧪 运行测试

```bash
pip install pytest pytest-asyncio
PYTHONPATH=src python -m pytest tests/ -v
```

**26 个测试用例** 分布在 3 个模块：
- `test_token_profiler.py` — Token 计数准确性
- `test_session_store.py` — CRUD 操作、Fork 图谱
- `test_context_engine.py` — 裁剪、修剪、注入

---

## 🗑 卸载

### 虚拟环境
```bash
deactivate
rm -rf /path/to/ContextOS
```

### pipx
```bash
pipx uninstall contextos
```

### pip
```bash
pip uninstall contextos
rm -f ./contextos.db    # 可选：删除数据
```

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)。
