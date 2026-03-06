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

5. Run the API:

```bash
venv/bin/python -m uvicorn app.main:app --reload
```

## What I Need From You (Supabase)

To fully wire the next phase, provide:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only; never expose in client code)
- `SUPABASE_DB_URL` (Postgres connection string from Supabase Database settings)

Current starter endpoints:

- `GET /health`
- `POST /memories` (requires bearer token)
- `GET /memories` (requires bearer token)
- `POST /search` (requires bearer token)
