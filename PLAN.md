# PLAN.md — agent-memory-patterns

## Open Decisions (must be resolved before implementation)

### 1. Embeddings provider for semantic memory (04)

Anthropic has no native embeddings API. Two viable options:

| Option | Provider | Notes |
|---|---|---|
| **A (Recommended)** | **Voyage AI** (`voyage-3-large`)  | Anthropic's own recommended partner; purpose-built for RAG; simple REST API; free tier available |
| B | OpenAI (`text-embedding-3-small`) | Widely known, free tier, but adds a second-brand dependency |

**Proposal:** Use Voyage AI. It aligns with Anthropic's recommendation, the SDK is one-pip install (`voyageai`), and it keeps the stack closer to the Claude ecosystem.

---

### 2. Redis's exact role

Two legitimate uses in this repo; they conflict if Redis is used for both:

| Option | Role | Folders |
|---|---|---|
| **A (Recommended)** | Redis as **recent-events cache** in front of Postgres for episodic memory (03); Postgres used directly for procedural memory (05) | 03, 05 |
| B | Redis as sole storage backend for procedural memory (05); no Redis in episodic | 05 only |

**Proposal:** Option A — Redis as a hot-events cache (last N events per user) for 03-episodic, with Postgres as the durable store. For 05-procedural, Postgres stores the routine definitions (they are long-lived structured data, not cache-friendly). This keeps each technology in the role it's best at.

---

### 3. Local runnability

Real services (Postgres, Redis, Pinecone) create friction for local dev. Two sub-decisions:

**3a. Postgres + Redis — `docker-compose.yml` at repo root**

Proposal: yes, include `docker-compose.yml` with:
- `postgres:16-alpine` on port 5432
- `redis:7-alpine` on port 6379

**3b. Pinecone local alternative**

| Option | Notes |
|---|---|
| **A (Recommended)** | `pgvector` extension on the same Postgres container — SQL-compatible, zero extra infra, Pinecone stays the documented default in README |
| B | `chromadb` — pure-Python in-process, but diverges more from Pinecone's API shape |

Proposal: `pgvector` (add `ankane/pgvector:latest` image to docker-compose, or enable extension on the same postgres image). Provide a `USE_PGVECTOR=true` env var toggle in 04-semantic-memory to switch between backends.

---

## Folder-by-folder plan

### `common/`

**Files:**
- `claude_client.py`

**Contents:**
- `get_client()` → returns `anthropic.Anthropic` instance (reads `ANTHROPIC_API_KEY` from env)
- `DEFAULT_MODEL` constant (read from env `CLAUDE_MODEL`, fallback to latest Sonnet via `claude-sonnet-4-6` — verified at implementation time against current Anthropic docs)
- `load_env()` → calls `python-dotenv` to load `.env`

No memory logic here — this is purely a thin SDK wrapper.

---

### `01-in-context-memory/`

**Files:** `README.md`, `memory.py`, `example.py`

**Schema:** None — everything is in Python memory (list).

**Key classes/functions:**

`memory.py`:
- `class InContextMemory` — wraps a `deque(maxlen=N)` of `{"role": str, "content": str}` dicts
  - `add_message(role, content)` — appends; oldest automatically drops when full
  - `get_messages()` → list of dicts for Claude API `messages` param
  - `token_count()` → approximate count (word-split heuristic, good enough for demo)

`example.py`:
- Sets `MAX_MESSAGES = 6` (small window to force forgetting quickly)
- Turn 1: user says "My name is Alice"
- Turns 2–5: unrelated filler exchanges (to push Alice out of the 6-message window)
- Turn 6: agent asked "What is my name?" — window no longer contains the name, agent answers "I don't know"
- Prints the window contents at each step so the forgetting is visually obvious

**Example output shape:**
```
[Turn 1] User: My name is Alice
[Window size: 2/6]

[Turn 2-5] ... filler ...
[Window size: 6/6 — oldest messages dropped]

[Turn 6] User: What is my name?
Assistant: I don't have that information in our current conversation.

--- Window does NOT contain "Alice" ---
```

---

### `02-external-memory/`

**Files:** `README.md`, `schema.sql`, `memory.py`, `example.py`

**Domain:** Customer order history

**Schema (`schema.sql`):**
```sql
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id TEXT        NOT NULL,
    item        TEXT        NOT NULL,
    quantity    INT         NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

**Key classes/functions:**

`memory.py`:
- `class ExternalMemory`
  - `__init__(conn_str)` — psycopg2 connection
  - `add_order(customer_id, item, quantity)` → inserts row, returns order id
  - `get_orders(customer_id)` → list of order dicts
  - `update_status(order_id, status)` → updates status field

`example.py`:
- **Session A** (function `session_a()`): connects to Postgres, inserts 3 orders for customer "C001", disconnects (simulates end of process)
- **Session B** (function `session_b()`): fresh connection, retrieves orders for "C001", feeds them to Claude as context, Claude summarizes the order history
- `main()` calls A then B sequentially but prints a separator showing the "process boundary"

---

### `03-episodic-memory/`

**Files:** `README.md`, `schema.sql`, `memory.py`, `example.py`

**Schema (`schema.sql`):**
```sql
CREATE TABLE episodes (
    id         SERIAL PRIMARY KEY,
    user_id    TEXT        NOT NULL,
    session_id TEXT        NOT NULL,
    role       TEXT        NOT NULL,  -- 'user' | 'agent'
    content    TEXT        NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_episodes_user ON episodes(user_id);
CREATE INDEX idx_episodes_session ON episodes(user_id, session_id);
```

**Redis role:** Cache of the last 20 events for a given `user_id` (key: `episodes:{user_id}`, type: Redis List, LPUSH + LTRIM). On miss, load from Postgres and repopulate.

**Key classes/functions:**

`memory.py`:
- `class EpisodicMemory`
  - `__init__(pg_conn_str, redis_url)` — both connections
  - `save_event(user_id, session_id, role, content)` — write to Postgres AND push to Redis list
  - `get_recent_events(user_id, n=20)` — try Redis first, fall back to Postgres SELECT ORDER BY occurred_at DESC LIMIT n
  - `get_session_events(user_id, session_id)` — Postgres only (full session, not just recent)

`example.py`:
- **Session 1**: user "U42" reports a billing issue; agent acknowledges and says it will follow up. Events saved.
- **Session 2** (new session_id, simulated later run): agent retrieves recent events for U42, sees the billing complaint, proactively opens with "I see from our last conversation that you had a billing issue..."
- Prints clearly: "Loading from Redis cache" or "Cache miss — loading from Postgres"

---

### `04-semantic-memory/`

**Files:** `README.md`, `memory.py`, `example.py`

**No `schema.sql`** — Pinecone manages index schema. For pgvector fallback, schema is in `memory.py` (inline CREATE TABLE).

**Pinecone index config:**
- Index name: `agent-semantic-memory`
- Dimension: 1024 (Voyage AI `voyage-3-large` output dim)
- Metric: cosine

**Key classes/functions:**

`memory.py`:
- `class SemanticMemory`
  - `__init__(use_pgvector=False)` — picks backend from env
  - `store_fact(fact_id, text, metadata)` — embed text via Voyage AI, upsert to Pinecone (or pgvector)
  - `retrieve_facts(query, top_k=3)` — embed query, similarity search, return list of `(score, metadata)` tuples

`example.py`:
- Store: "The user prefers metric units over imperial"
- Store 2 filler facts unrelated to units
- Query: "What measurement system does this person like?" (different wording)
- Top result should be the metric preference
- Feed preference to Claude; Claude answers a distance question in kilometers automatically
- Print the retrieved fact + score to show the semantic match worked

---

### `05-procedural-memory/`

**Files:** `README.md`, `schema.sql`, `memory.py`, `example.py`

**Schema (`schema.sql`):**
```sql
CREATE TABLE procedures (
    id          SERIAL PRIMARY KEY,
    name        TEXT        NOT NULL UNIQUE,
    description TEXT        NOT NULL,
    steps       JSONB       NOT NULL,  -- ordered list of step objects
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_count  INT         NOT NULL DEFAULT 0
);
```

**Step object shape (JSONB):**
```json
{ "step": 1, "action": "fetch_weather", "params": {"location": "{city}"}, "description": "Get current weather" }
```

**Key classes/functions:**

`memory.py`:
- `class ProceduralMemory`
  - `__init__(conn_str)`
  - `store_procedure(name, description, steps)` — upsert by name
  - `load_procedure(name)` → list of step dicts or None
  - `increment_usage(name)` → bumps `used_count`
  - `list_procedures()` → names + descriptions

`example.py`:
- **First run** (`--mode=first`): agent receives task "generate a weekly report"; no procedure stored yet → agent reasons through steps (fetch data, aggregate, format, send); steps captured and stored under name "weekly_report"
- **Second run** (`--mode=replay`): agent receives same task; loads stored procedure; replays steps, prints `[FROM STORED PROCEDURE]` prefix for each step vs `[FRESH REASONING]` for any new steps
- Difference is visually unmistakable in output

---

### Root `README.md`

One-page overview:
- What this repo is (5 memory types, each standalone)
- Quick-start (clone, copy `.env.example`, docker-compose up)
- Table linking to each folder with one-line description
- LinkedIn post link placeholder

---

### `requirements.txt` (planned dependencies)

```
anthropic
voyageai
psycopg2-binary
redis
pinecone-client
python-dotenv
pgvector          # for local pgvector fallback only
```

---

### `.env.example`

```
ANTHROPIC_API_KEY=
VOYAGE_API_KEY=
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agent_memory
REDIS_URL=redis://localhost:6379/0
CLAUDE_MODEL=claude-sonnet-4-6
USE_PGVECTOR=false
```

---

### `docker-compose.yml`

Services:
- `postgres` — `ankane/pgvector:latest` (includes pgvector extension), port 5432, DB `agent_memory`
- `redis` — `redis:7-alpine`, port 6379

---

## Implementation order (after approval)

1. `common/`
2. `01-in-context-memory/`
3. `02-external-memory/`
4. `03-episodic-memory/`
5. `04-semantic-memory/`
6. `05-procedural-memory/`
7. Root `README.md`, `requirements.txt`, `.env.example`, `docker-compose.yml`
8. Initial git commit + push to GitHub

---

## Questions for you (before I write any code)

The three Open Decisions above need your call:

1. **Embeddings provider** — Voyage AI (recommended) or OpenAI?
2. **Redis role** — cache layer for episodic memory + Postgres for procedural (recommended), or Redis as procedural storage?
3. **Local runnability** — include `docker-compose.yml` + `pgvector` toggle (recommended), or assume users have their own services?

Also one additional question:

4. **GitHub repo** — do you have a repo already created, or should I include instructions for you to create one? (I won't `git push` without your go-ahead.)
