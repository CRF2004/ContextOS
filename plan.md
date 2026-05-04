# 一、需求定义（重新收敛版本）

你这个系统不要一开始就做“Agent OS”，否则会失控。

我们把需求压缩成 4 个核心能力：

------

## 1️⃣ Context 可观测（必须）

目标：你要“看见 Claude 在怎么用 token”

能力：

- 总 token 使用
- MCP tool token 占比
- skill prompt injection 占比
- 历史消息增长曲线

👉 输出：

```
{
  "total_tokens": 120000,
  "mcp_tokens": 30000,
  "skill_tokens": 15000,
  "messages_tokens": 75000
}
```

------

## 2️⃣ Context 控制（核心）

目标：你可以“改 Claude 的输入”

能力：

- context 压缩（summarize history）
- tool pruning（控制 MCP）
- prompt injection（skill）
- context window trimming

------

## 3️⃣ Session 管理（必须）

目标：你可以“管理对话生命周期”

能力：

- session 创建
- session 保存
- session restore
- session fork（手动 + 半自动）

------

## 4️⃣ Fork（v1 重点）

目标：解决你现在的痛点：

> context 爆炸 + 长任务断裂

能力：

- 手动 fork
- 条件 fork（token /任务复杂度）
- fork graph

------

# 二、初步架构设计（现实可落地）

这里我给你一个**能直接开 repo 的结构**。

------

## 🔷 系统架构（v0-v1）

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

------

## 🔷 核心设计原则（很重要）

### ✔ 1. Proxy-first

所有请求必须经过 proxy

------

### ✔ 2. Orchestrator 不依赖 Claude Code 内部

（避免 SDK lock-in）

------

### ✔ 3. 所有能力都基于 request/response hook

------

# 三、核心模块拆解（工程级）

------

## 1️⃣ Proxy Layer（最重要）

### 职责：

- intercept request
- intercept response
- inject context modifications

------

### 做法：

```
POST /v1/messages → your proxy
```

内部流程：

```
client request
   ↓
context profiler
   ↓
context engine (rewrite)
   ↓
Claude API
   ↓
response profiler
   ↓
session store
```

------

## 2️⃣ Token Profiler（必须）

### 功能：

- 计算 prompt tokens
- MCP tool tokens
- skill tokens

------

### 技术实现：

- tiktoken / anthropic tokenizer
- MCP schema size estimation
- message-level token tracking

------

## 3️⃣ Context Engine（核心）

### 功能：

#### A. context压缩

```
def compress(messages):
    return summarize(messages[:-k]) + recent_messages
```

------

#### B. tool pruning

```
def prune_tools(tools, budget):
    return sorted(tools, key=relevance)[:budget]
```

------

#### C. skill injection

```
system_prompt += selected_skill_prompt
```

------

## 4️⃣ Fork Engine（v1重点）

### fork触发条件：

```
if (
    token_usage > 0.75 * limit
    or task_complexity > threshold
    or tool_conflict_detected
):
    fork_session()
```

------

### fork内容：

```
{
  "parent_session": "A",
  "summary": "...",
  "carried_state": {
    "goal": "...",
    "files": ["..."],
    "constraints": "..."
  }
}
```

------

## 5️⃣ Session Store

最简单版本：

- SQLite（够用）
- 后面再换 Postgres

------

# 四、初步实现路径（非常关键）

我帮你拆成 **3 个阶段（每阶段都有产出）**

------

# 🥇 Phase 1（最小可运行系统）

> 目标：你能“看到 Claude token 是怎么爆的”

------

### 做三件事：

## 1. proxy server

- FastAPI
- forward Claude API

------

## 2. token logger

- request token
- response token

------

## 3. session storage

- SQLite

------

### 产出：

✔ CLI可用
 ✔ 能记录所有请求
 ✔ 能看 token 曲线

------

# 🥈 Phase 2（可控系统）

> 目标：你可以“控制 context”

------

### 加入：

## 1. context trimming

- 历史压缩

## 2. tool pruning

- MCP控制

## 3. skill injection

- system prompt管理

------

### 产出：

✔ token下降
 ✔ context可控
 ✔ tool不会爆炸

------

# 🥉 Phase 3（核心产品形态）

> 目标：自动 fork + graph

------

### 加入：

## 1. fork engine

- 手动 fork
- 自动 fork

## 2. session graph

- React Flow

## 3. replay system

- session回放

------

### 产出：

✔ session tree
 ✔ 自动分叉
 ✔ 可视化系统

------

# 五、最终产品形态（你真正要做的）

如果做完，你的系统不是：

> ❌ MCP tool manager
>  ❌ skill generator

而是：

> ✔ **Claude Execution Runtime**
>  ✔ **Context Operating System**

------

# 六、最关键的设计判断（帮你避免走偏）

### ❌ 不要做：

- skill compiler
- MCP registry
- agent framework

------

### ✔ 只做三件事：

1. proxy（必须）
2. context engine（核心）
3. fork engine（差异化）
