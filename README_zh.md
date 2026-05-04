# ContextOS

**Context Operating System — Claude 对话 Context 控制与 Session 管理系统**

ContextOS 是一个面向 Claude Code / Claude API 的中间层系统，通过 Proxy 拦截请求/响应，实现 Token 可观测、Context 压缩、Tool 裁剪、Session Fork 等能力，解决长对话 Context 爆炸和长任务断裂的问题。

## 快速开始

```bash
# 1. 安装依赖
cd /mnt/chengrongfeng_private/cc_dump/ContextOS
pip install fastapi uvicorn httpx aiosqlite pydantic python-dotenv tiktoken

# 2. 启动服务
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199

# 或使用 PYTHONPATH
PYTHONPATH=src ANTHROPIC_API_KEY=sk-ant-... python -m contextos.cli run --port 8199
```

### CLI 命令

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

## 实现进度

### Phase 1 — 最小可运行系统 ✅
- [x] FastAPI Proxy Server 转发 Claude API
- [x] Token Logger 记录请求/响应 Token 用量
- [x] SQLite Session Storage
- [x] CLI 可用
- [x] 请求日志记录
- [x] Token 曲线查询
- [x] 26 个测试用例全部通过

### Phase 2 — 可控系统 (代码已实现，待集成测试)
- [x] Context Trimming（历史压缩）
- [x] Tool Pruning（MCP 控制）
- [x] Skill Injection（System Prompt 管理）

### Phase 3 — 核心产品形态 (代码已实现，待前端)
- [x] Fork Engine（手动 + 自动 Fork）
- [x] Fork Graph（BFS 遍历 parent/child 链路）
- [ ] Session Graph 可视化（React Flow）
- [ ] Replay System（Session 回放）

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

## 相关文件

- [plan.md](./plan.md) — 详细的需求定义、架构设计和实现路线
