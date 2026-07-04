# 04 — Semantic Memory

## What it is
Facts and preferences stored as vector embeddings in Pinecone (or pgvector locally), retrieved by semantic similarity. The query doesn't need to match stored text exactly — meaning is matched, not keywords.

## Why it's used
Users rarely phrase queries the same way twice. Semantic memory lets an agent retrieve "user prefers metric units" in response to "what measurement system does this person like?" — zero keyword overlap, correct result.

## When to use it
- Storing user preferences, beliefs, or domain knowledge that should be recalled by meaning
- Knowledge bases queried with natural language
- Any situation where exact-match retrieval would fail due to paraphrase
- Personalization systems that accumulate facts about a user over time

## When NOT to use it
- Structured data with known fields — use SQL (External Memory)
- Timestamped event logs — use Episodic Memory
- Facts that change frequently (vector stores are append/upsert, not transactional)

## Embeddings provider
This folder uses **Voyage AI** (`voyage-3-large`, 1024 dimensions) — Anthropic's recommended partner for embeddings. Anthropic does not offer a native embeddings API.

Set `VOYAGE_API_KEY` in your `.env` file. Sign up at [voyageai.com](https://www.voyageai.com).

## Pinecone setup
Create an index named `agent-semantic-memory` with:
- Dimension: `1024`
- Metric: `cosine`

Set `PINECONE_API_KEY` in `.env`.

## Local alternative (pgvector)
Set `USE_PGVECTOR=true` in `.env` to use the pgvector Postgres extension instead of Pinecone. No Pinecone account needed. Requires the `ankane/pgvector` Docker image (included in `docker-compose.yml`).

## Example
`example.py` stores 3 facts (one metric preference, two fillers), then queries with different wording and shows the semantic match. Claude then answers a distance question automatically in the user's preferred units.

```bash
# With Pinecone (default)
cd 04-semantic-memory
python example.py

# With local pgvector
USE_PGVECTOR=true python example.py
```
