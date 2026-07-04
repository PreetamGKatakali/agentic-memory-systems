# Agent Memory Patterns

A reference implementation of the 5 types of AI agent memory — each as a standalone, runnable Python folder with working code backed by real production-grade services.

> Companion code for the LinkedIn carousel on AI agent memory types.

---

## The 5 types

| # | Type | Storage | Key trait |
|---|------|---------|-----------|
| [01](./01-in-context-memory/) | **In-Context** | Python deque (no DB) | Lives only in the prompt window; forgotten once the window slides |
| [02](./02-external-memory/) | **External** | Postgres | Survives across sessions and process restarts |
| [03](./03-episodic-memory/) | **Episodic** | Postgres + Redis cache | Recalls specific past events with timestamps and session IDs |
| [04](./04-semantic-memory/) | **Semantic** | Pinecone / pgvector | Retrieves facts by meaning, not keyword match |
| [05](./05-procedural-memory/) | **Procedural** | Postgres | Stores reusable multi-step routines; replays without re-planning |

---

## Quick start

### 1. Clone and install

```bash
git clone <repo-url>
cd agent-memory-patterns
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, VOYAGE_API_KEY, PINECONE_API_KEY
```

### 3. Start local services (Postgres + Redis)

```bash
docker-compose up -d
```

This starts:
- **Postgres** (with pgvector extension) on port 5432
- **Redis** on port 6379

### 4. Run any example

Each folder is fully standalone:

```bash
python 01-in-context-memory/example.py
python 02-external-memory/example.py
python 03-episodic-memory/example.py
python 04-semantic-memory/example.py
python 05-procedural-memory/example.py --mode=first
python 05-procedural-memory/example.py --mode=replay
```

---

## No Pinecone account? Use pgvector

Set `USE_PGVECTOR=true` in `.env`. The `ankane/pgvector` image in `docker-compose.yml` provides the vector extension on the same Postgres instance — no extra services needed.

---

## Stack

- **LLM**: Anthropic Claude (`anthropic` Python SDK)
- **Embeddings**: Voyage AI `voyage-3-large` (Anthropic's recommended embeddings partner)
- **Vector store**: Pinecone (default) or pgvector (local alternative)
- **Relational DB**: Postgres 16
- **Cache**: Redis 7
- **Language**: Python 3.11+

---

## Design principles

- **No shared orchestrator** — each folder runs independently with no cross-imports
- **Real services only** — Postgres, Redis, Pinecone; no toy in-memory substitutes
- **Forgetting is observable** — folder 01 makes the sliding window effect visible in output
- **Process boundaries are real** — folder 02 Session B has zero shared in-memory state with Session A
