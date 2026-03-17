# Open Brain

Open Brain is a personal long-term memory layer for AI agents and assistants.

It provides:
- a versioned REST API (`/v1`)
- a local MCP-style bridge (`stdio`) for tool-driven workflows
- semantic memory retrieval on Supabase Postgres + pgvector

## Current Implementation Status

Implemented:
- Memory CRUD (`create/list/get/update/delete`)
- Hybrid write flow:
  - `POST /v1/memories/suggest` (suggest candidate memories)
  - `POST /v1/memories/remember` (explicit persist)
- Semantic retrieval:
  - `POST /v1/search`
  - cosine similarity + recency boost + optional filters + score threshold
  - light entity boost via memory-entity links
- NDJSON portability:
  - `POST /v1/memories/export`
  - `POST /v1/memories/import` (`skip_existing` / `upsert`)
- Health endpoints:
  - `GET /health` (legacy)
  - `GET /v1/health`
  - `GET /v1/health/db`
- Request IDs + structured error responses
- Alembic migrations (replacing ad-hoc schema bootstrap)
- Embedding provider abstraction:
  - OpenAI embeddings
  - deterministic local fallback

## Tech Stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy + Alembic
- Supabase Postgres + pgvector
- pytest

## Local Setup

### 1) Create virtual environment

```bash
python3 -m venv venv
```

### 2) Install dependencies

```bash
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -e ".[dev]"
```

### 3) Create `.env`

```bash
cp .env.example .env
```

Fill these variables:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- `OPEN_BRAIN_API_TOKEN`
- `EMBEDDING_PROVIDER` (`local`, `openai`, or `auto`)
- `OPENAI_API_KEY` (required if `openai` or `auto` with OpenAI enabled)
- `OPENAI_EMBED_MODEL` (default `text-embedding-3-small`)

Important for Supabase:
- Use **Session Pooler** URI when on IPv4-only networks.
- `SUPABASE_DB_URL` should use `postgresql+psycopg://...`.
- URL-encode DB passwords with special chars (`#`, `@`, `!`, `%`).

### 4) Run DB migrations

```bash
venv/bin/python scripts/init_db.py
```

This runs Alembic `upgrade head`.

### 5) Start API

```bash
venv/bin/python -m uvicorn app.main:app --reload
```

### 6) Run tests

```bash
venv/bin/python -m pytest -q
```

## Command Reference

- `make venv`: create virtual environment
- `make install`: install runtime + dev dependencies
- `make init-db`: run Alembic migrations to latest version
- `make migrate`: alias for `alembic upgrade head`
- `make run`: run FastAPI dev server
- `make test`: run pytest
- `make mcp-bridge`: run local stdio bridge for `remember` / `recall`

## API Quick Examples

All protected endpoints require:

```http
Authorization: Bearer <OPEN_BRAIN_API_TOKEN>
```

Create memory:

```bash
curl -X POST http://127.0.0.1:8000/v1/memories \
  -H "Authorization: Bearer <OPEN_BRAIN_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"content":"I prefer concise explanations","memory_type":"preference","source":"manual","tags":["style"],"confidence":0.9}'
```

Suggest memory (non-persistent):

```bash
curl -X POST http://127.0.0.1:8000/v1/memories/suggest \
  -H "Authorization: Bearer <OPEN_BRAIN_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"text":"I prefer practical, concise answers"}'
```

Semantic search:

```bash
curl -X POST http://127.0.0.1:8000/v1/search \
  -H "Authorization: Bearer <OPEN_BRAIN_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query":"What are my response preferences?","top_k":5,"recency_weight":0.2,"score_threshold":0.15}'
```

## MCP Bridge (Local)

Run:

```bash
make mcp-bridge
```

Input (stdin JSON line):

```json
{"action":"remember","payload":{"content":"I am building Open Brain","memory_type":"project"}}
```

```json
{"action":"recall","payload":{"query":"What project am I building?","top_k":3}}
```

This is a local bridge layer that keeps tool contracts stable while a stricter full MCP protocol adapter is expanded.
