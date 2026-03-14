# Open Brain

## Problem statement and mission:

Open Brain is a personal memory layer for AI assistants.

It gives different LLM tools a shared long-term memory, so your context does not reset every time you switch providers or start a new session.

I am building this to act as something anyone can get running locally in just a couple of minutes, and to learn more about embeddings and AI engineering.

## Technologies

- Python + FastAPI
- Supabase Postgres
- `pgvector` (vector similarity in Postgres)
- SQLAlchemy
- MCP (Model Context Protocol) tool surface (starter stub)

## Quick Start

1. Create a virtual environment named `venv`:

```bash
python3 -m venv venv
```

2. Install dependencies:

```bash
venv/bin/pip install --upgrade pip
venv/bin/pip install -e ".[dev]"
```

3. Configure environment:

```bash
cp .env.example .env
```

4. Fill `.env` with your Supabase values, then initialize the database:

```bash
venv/bin/python scripts/init_db.py
```

If `scripts/init_db.py` fails with a malformed URL error, URL-encode the DB password first (especially if it contains `#`, `@`, `!`, `%`).

5. Run the API:

```bash
venv/bin/python -m uvicorn app.main:app --reload
```

Current starter endpoints:

- `GET /health`
- `POST /memories` (requires bearer token)
- `GET /memories` (requires bearer token)
- `GET /memories/{id}` (requires bearer token)
- `PATCH /memories/{id}` (requires bearer token)
- `DELETE /memories/{id}` (requires bearer token)
- `POST /search` (requires bearer token)

## Current Search Behavior

`POST /search` now uses:

- deterministic local embeddings (no external API key required yet)
- pgvector cosine similarity
- optional filters: `memory_type`, `source`
- recency boost control via `recency_weight` (0.0 to 1.0)
- returns a `score` per result
