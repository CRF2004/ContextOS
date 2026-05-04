# ContextOS

**Claude Context Operating System**

A transparent proxy layer for the Claude API that provides Token observability, context control, session management, and session fork capabilities — solving context explosion in long conversations and task interruption issues.

[中文版](./README_zh.md)

---

## Features

- **Token Observability** — Real-time prompt/completion token breakdown, stored and visualized
- **Session Management** — Create, query, archive sessions with SQLite persistence
- **Session Fork** — Branch conversations with parent/child lineage tracking, auto-fork at token thresholds
- **Context Engine** — Message trimming, tool pruning, skill injection for context window control
- **API Proxy** — Transparent Claude API proxy with request/response interception and logging
- **Web Dashboard** — React-based SPA with React Flow fork graphs and Recharts token visualizations
- **CLI** — Command-line tools for quick operations

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+ (for frontend)
- An [Anthropic API Key](https://console.anthropic.com/settings/keys)

### Installation

#### Option A: Virtual Environment (recommended for testing)

```bash
git clone https://github.com/CRF2004/ContextOS.git
cd ContextOS

# Create isolated environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -e ".[dev]"

# Run server
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199
```

#### Option B: pipx (cleanest — no venv activation needed)

```bash
pipx install git+https://github.com/CRF2004/ContextOS.git
ANTHROPIC_API_KEY=sk-ant-... contextos run --port 8199
```

#### Option C: Without installation

```bash
git clone https://github.com/CRF2004/ContextOS.git
cd ContextOS
pip install fastapi uvicorn httpx aiosqlite pydantic python-dotenv tiktoken
PYTHONPATH=src ANTHROPIC_API_KEY=sk-ant-... python -m contextos.cli run --port 8199
```

### Frontend

```bash
cd web
npm install
npm run build    # builds to ../dist/web (served by FastAPI)
```

### Docker

```bash
# Coming soon
```

---

## CLI

```bash
# Start the proxy server
contextos run --port 8199 --db ./contextos.db --api-key sk-ant-...

# List all sessions
contextos sessions

# View token usage
contextos tokens <session_id>

# View request logs
contextos logs <session_id>
```

---

## API Endpoints

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sessions` | Create a new session |
| `GET`  | `/api/sessions` | List all sessions |
| `GET`  | `/api/sessions/{id}` | Get session details |
| `POST` | `/api/sessions/{id}/archive` | Archive a session |

### Token Observability

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/sessions/{id}/tokens` | Token usage summary |
| `GET`  | `/api/sessions/{id}/tokens/history` | Token history timeline |
| `GET`  | `/api/sessions/{id}/requests` | Request logs |
| `POST` | `/api/tokens/count` | Count tokens in text |

### Context Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/context/stats` | Get context token statistics |

### Session Fork

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sessions/{id}/fork` | Fork a session |
| `GET`  | `/api/sessions/{id}/fork-graph` | Get fork relationship graph |

### Proxy

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/proxy/messages?session_id=xxx` | Forward request to Claude API |

---

## Project Structure

```
ContextOS/
├── src/contextos/
│   ├── server.py           # FastAPI application entry
│   ├── proxy.py            # Proxy layer — intercept & forward Claude API
│   ├── token_profiler.py   # Token profiler — tiktoken-based counting
│   ├── session_store.py    # SQLite persistence
│   ├── context_engine.py   # Context trimming / tool pruning / skill injection
│   ├── fork_engine.py      # Session fork engine
│   ├── models.py           # Pydantic data models
│   └── cli.py              # CLI entry point
├── web/src/
│   ├── App.tsx             # React router with sidebar navigation
│   ├── api/client.ts       # TypeScript API client
│   └── pages/              # Dashboard pages: sessions, tokens, fork graph, logs
├── tests/
├── pyproject.toml
├── plan.md                 # Design docs & implementation roadmap
└── README_zh.md            # Chinese version of this README
```

---

## Architecture

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
            │        Proxy Layer (core)        │
            │  Claude Code / API Intercept    │
            └─────────┬───────────────────────┘
                      │
                 Claude API
```

---

## Design Principles

1. **Proxy-first** — All requests must go through the proxy
2. **SDK-independent** — No Claude Code SDK lock-in
3. **Hook-based** — All capabilities implemented via request/response hooks
4. **Not a Skill Compiler / MCP Registry / Agent Framework** — Focused scope

---

## Running Tests

```bash
pip install pytest pytest-asyncio
PYTHONPATH=src python -m pytest tests/ -v
```

26 tests across 3 modules — all passing.

---

## Uninstallation

### Option A (venv)

```bash
deactivate                  # Leave the virtual environment
rm -rf /path/to/ContextOS   # Delete the project directory
```

That's it — everything is self-contained in the `.venv` folder, no system files were modified.

### Option B (pipx)

```bash
pipx uninstall contextos
```

### Option C (pip)

```bash
pip uninstall contextos     # If installed via `pip install -e .`
```

Clean up any generated data files:

```bash
rm -f ./contextos.db        # SQLite database
rm -rf dist/web             # Built frontend assets
```

---

## License

MIT
