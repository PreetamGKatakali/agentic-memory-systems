# 02 — External Memory

## What it is
Persistent storage in a real database (Postgres) that survives beyond any single process or session. The agent reads and writes records just like any other backend application.

## Why it's used
Decouples memory from the agent process. Data written in Session A is immediately available to Session B — even if A has fully exited and B starts hours later.

## When to use it
- Order history, user records, logs, or any structured data that must persist
- Multi-agent systems where agents need shared state
- Any time you need to query, filter, or aggregate memories (SQL is more powerful than a prompt)
- Audit trails that must survive process crashes

## When NOT to use it
- Short conversations with no need for cross-session recall
- Unstructured or fuzzy data better served by vector search (see 04-semantic-memory)
- High-frequency writes where database overhead is prohibitive

## Example
`example.py` runs two sessions back-to-back with a visible process boundary between them:

- **Session A**: connects to Postgres, inserts 3 orders for customer `C001`, closes the connection.
- **Session B**: opens a fresh connection, reads back those orders, and feeds them to Claude for a summary.

```bash
# Start Postgres (from repo root)
docker-compose up -d postgres

# Apply schema and run
cd 02-external-memory
python example.py
```

Session B cannot see Session A's in-memory state — it has none. Everything comes from Postgres.
