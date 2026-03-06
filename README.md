# Open Brain

Open Brain is a personal memory layer for AI assistants.

The goal is to store useful long-term context (facts, preferences, projects, and history) in one place so different LLM tools can access the same memory instead of starting from scratch each session.

The project is designed to be local-first and standards-based, using MCP so multiple AI clients can connect to a shared memory backend.

## Technologies (planned)

- Python + FastAPI for the API and service layer
- PostgreSQL for durable storage
- pgvector for semantic search over embeddings
- MCP (Model Context Protocol) for tool integration across AI clients
- Docker Compose for local development
