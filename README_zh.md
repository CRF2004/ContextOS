# ContextOS

**Context Operating System — Claude 对话 Context 控制与 Session 管理系统**

ContextOS 是一个面向 Claude Code / Claude API 的中间层系统，通过 Proxy 拦截请求/响应，实现 Token 可观测、Context 压缩、Tool 裁剪、Session Fork 等能力，解决长对话 Context 爆炸和长任务断裂的问题。

[English](./README.md)

## 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+（前端构建可选）
- [Anthropic API Key](https://console.anthropic.com/settings/keys)

### 安装方式

#### 方式 A：虚拟环境（推荐，隔离测试）

```bash
git clone https://github.com/CRF2004/ContextOS.git
cd ContextOS

# 创建隔离环境
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 安装依赖
pip install -e ".[dev]"

# 启动服务
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199
```

#### 方式 B：pipx（最干净，无需激活 venv）

```bash
pipx install git+https://github.com/CRF2004/ContextOS.git
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199
```

#### 方式 C：不安装，直接运行

```bash
git clone https://github.com/CRF2004/ContextOS.git
cd ContextOS
pip install fastapi uvicorn httpx aiosqlite pydantic python-dotenv tiktoken
PYTHONPATH=src ANTHROPIC_API_KEY=sk-ant-... python -m contextos.cli run --port 8199
```

### 前端构建

```bash
cd web
npm install
npm run build    # 构建产物输出到 ../dist/web，由 FastAPI 直接服务
```

---

## CLI 命令

```bash
# 启动 Proxy 服务
contextos run --port 8199 --db ./contextos.db --api-key sk-ant-...

# 列出所有 Session
contextos sessions

# 查看 Token 用量
contextos tokens <session_id>

# 查看请求日志
contextos logs <session_id>
```

## API 端点

### Session 管理
| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/sessions` | 创建新 Session |
| GET | `/api/sessions` | 列出 Sessions |
| GET | `/api/sessions/{id}` | 获取 Session 详情 |
| POST | `/api/sessions/{id}/archive` | 归档 Session |

### Token 观测
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/sessions/{id}/tokens` | Token 用量汇总 |
| GET | `/api/sessions/{id}/tokens/history` | Token 历史曲线 |
| GET | `/api/sessions/{id}/requests` | 请求日志 |
| POST | `/api/tokens/count` | 文本 Token 计数 |

### Context 控制
| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/context/stats` | Context Token 统计 |

### Session Fork
| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/sessions/{id}/fork` | 分叉 Session |
| GET | `/api/sessions/{id}/fork-graph` | Fork 关系图 |

### Proxy
| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/proxy/messages?session_id=xxx` | 转发 Claude API 请求 |

## 项目结构

```
ContextOS/
├── src/contextos/
│   ├── server.py          # FastAPI 应用入口
│   ├── proxy.py           # Proxy 层 — 拦截/转发 Claude API
│   ├── token_profiler.py  # Token 分析器 — tiktoken 计数
│   ├── session_store.py   # SQLite 持久化
│   ├── context_engine.py  # Context 裁剪/工具修剪/Skill注入
│   ├── fork_engine.py     # Session 分叉引擎
│   ├── models.py          # Pydantic 数据模型
│   └── cli.py             # CLI 入口
├── tests/
├── pyproject.toml
└── plan.md
```

## 架构设计

```
                 ┌──────────────────────┐
                 │     Web Dashboard     │
                 │ (session + graph UI)  │
                 └─────────┬────────────┘
                           │
                 ┌─────────▼────────────┐
                 │   Orchestrator API    │
                 │     (FastAPI)         │
                 ├─────────┬────────────┤
                 │         │            │
     ┌───────────▼───┐ ┌──▼──────────┐ ┌▼─────────────┐
     │ Context Engine │ │ Fork Engine │ │ Token Profiler│
     └───────────┬───┘ └────┬────────┘ └────┬─────────┘
                 │           │               │
                 └────┬──────┴──────┬──────┘
                      │             │
            ┌─────────▼─────────────▼─────────┐
            │        Proxy Layer (关键)        │
            │  Claude Code / API Intercept    │
            └─────────┬───────────────────────┘
                      │
                 Claude API
```

## 设计原则

1. **Proxy-first：** 所有请求必须经过 Proxy
2. **不依赖 Claude Code 内部：** 避免 SDK lock-in
3. **基于 Request/Response Hook：** 所有能力都通过 Hook 实现
4. **不做 Skill Compiler / MCP Registry / Agent Framework**

## 运行测试

```bash
pip install pytest pytest-asyncio
PYTHONPATH=src python -m pytest tests/ -v
```

## 卸载

### 方式 A（venv）

```bash
deactivate                  # 退出虚拟环境
rm -rf /path/to/ContextOS   # 删除项目目录
```

一切都在 `.venv` 目录内，没有修改系统文件，删除即可。

### 方式 B（pipx）

```bash
pipx uninstall contextos
```

### 方式 C（pip）

```bash
pip uninstall contextos     # 如果通过 `pip install -e .` 安装
```

清理生成的数据文件：

```bash
rm -f ./contextos.db        # SQLite 数据库
rm -rf dist/web             # 构建的前端资源
```

---

## 相关文件

- [plan.md](./plan.md) — 详细的需求定义、架构设计和实现路线
