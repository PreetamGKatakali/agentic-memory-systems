# Project: agent-memory-patterns

## What this repo is

A reference implementation of the 5 types of AI agent memory: **In-Context, External, Episodic, Semantic, Procedural**. Each type gets its own standalone, runnable folder with working code, not just notes. This backs a LinkedIn post/carousel explaining the concepts — this repo is the "here's the code" follow-through.

## Stack

- **Language:** Python 3.11+
- **LLM:** Anthropic Claude API (`anthropic` Python SDK). Do not hardcode a model string from memory — check current model names in the Anthropic docs before using one.
- **Storage:** Postgres, Redis, Pinecone (production-like, not toy/in-memory substitutes — this is the whole point of the repo).
- **Env vars:** `.env` file, never commit secrets. Provide `.env.example`.

## CRITICAL: process — do not skip this

1. **Step 1 — Plan only.** Read this whole file, then write `PLAN.md` at the repo root. `PLAN.md` must cover, per folder: file list, DB/index schema, key functions/classes, and the exact example flow that will be demoed. **Do not write any implementation code in this step.**
2. **Step 2 — Flag open decisions in `PLAN.md`** under a section called "Open Decisions" (see list near the bottom of this doc). Do not silently pick an approach for these — propose 1-2 options each and wait for a decision.
3. **Stop after `PLAN.md` and wait for explicit approval before writing code.**
4. **Step 3 — Implement**, only after approval, in this order: `common/` → `01-in-context-memory` → `02-external-memory` → `03-episodic-memory` → `04-semantic-memory` → `05-procedural-memory` → root `README.md`.
5. Each folder must be **fully standalone** — no shared orchestrator agent tying all 5 together, and no cross-imports between numbered folders. A small `common/` module is allowed only for a thin shared Claude API client wrapper and config/env loading — nothing memory-specific.

## Repo structure to plan for

```
agent-memory-patterns/
├── README.md                 (root overview, links to each folder, mirrors the 5-type carousel)
├── PLAN.md                   (written first, before any code)
├── requirements.txt
├── .env.example
├── common/
│   └── claude_client.py      (thin Anthropic SDK wrapper + env/config loading only)
├── 01-in-context-memory/
│   ├── README.md
│   ├── memory.py
│   └── example.py
├── 02-external-memory/
│   ├── README.md
│   ├── schema.sql             (Postgres schema)
│   ├── memory.py
│   └── example.py
├── 03-episodic-memory/
│   ├── README.md
│   ├── schema.sql
│   ├── memory.py
│   └── example.py
├── 04-semantic-memory/
│   ├── README.md
│   ├── memory.py
│   └── example.py
└── 05-procedural-memory/
    ├── README.md
    ├── schema.sql
    ├── memory.py
    └── example.py
```

Every numbered folder's `README.md` must follow this exact shape (matches the carousel format, keep it consistent):
- **What it is**
- **Why it's used**
- **When to use it**
- **When NOT to use it**
- **Example** (concrete, tied to the code in that folder, not generic)

## Per-folder spec

### 01 — In-Context Memory
- No persistence. Simulate a real token-windowed context (e.g. a sliding list of recent messages with a max size).
- Demo must show a fact getting pushed out of the window and the agent failing to recall it afterward — the "forgotten once window slides" behavior has to be visible in the example output, not just described.

### 02 — External Memory
- Postgres-backed persistent store (orders/records/logs — pick one concrete domain, e.g. customer order history).
- Demo must run as two separate processes/sessions: session A writes data, session B (fresh process, no shared in-memory state) reads it back. This proves it survives beyond a single run, unlike folder 01.

### 03 — Episodic Memory
- Postgres for durable storage of timestamped events tied to a user/session ID. Redis may be used as a recent-events cache in front of Postgres — Claude Code should propose this in PLAN.md rather than assume it.
- Demo: agent handles a support-style interaction, then in a later "session" recalls and follows up on that specific past event (not just a general fact about the user — that's semantic memory's job, keep the distinction sharp in the code).

### 04 — Semantic Memory
- Pinecone-backed vector store for durable facts/preferences, retrieved by meaning.
- Anthropic does not have a first-party embeddings endpoint — this needs a real decision (see Open Decisions below), don't silently assume one.
- Demo: store a preference once ("user prefers metric units"), retrieve it by semantic similarity in a differently-worded later query, and show the agent applying it automatically.

### 05 — Procedural Memory
- Storage for reusable multi-step routines (a named sequence of steps/tool calls), not facts or events. Postgres or Redis — Claude Code should propose in PLAN.md.
- Demo: agent executes a multi-step routine once, stores it, then on a later run retrieves and replays the stored routine instead of re-planning it from scratch. Make the "re-planning avoided" difference observable (e.g. log/print when a step came from stored procedure vs fresh reasoning).

## Open Decisions (must be flagged in PLAN.md, not assumed)

1. **Embeddings provider for semantic memory** — Anthropic has no native embeddings API. Propose options (e.g. Voyage AI, which Anthropic recommends, vs. another provider) and note the tradeoff.
2. **Redis's exact role** — cache in front of Postgres for episodic memory, storage for procedural routines, both, or neither. Propose and justify.
3. **Local runnability** — Postgres/Redis/Pinecone are real cloud/production services. Propose a `docker-compose.yml` for local Postgres + Redis, and a local Pinecone alternative (e.g. `pgvector` extension) for anyone without a paid Pinecone account, while keeping Pinecone as the documented default in each README.

## Non-goals

- No combined orchestrator agent using all 5 memory types together. Keep each folder independently runnable and understandable on its own.
- No frontend/UI. This is backend/library code plus example scripts, run from the terminal.