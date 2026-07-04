# 03 — Episodic Memory

## What it is
Timestamped event logs tied to a specific user and session ID, stored durably in Postgres with a Redis cache for fast retrieval of recent events. Unlike semantic memory (facts/preferences), episodic memory records *what happened* — specific interactions with time and context.

## Why it's used
Agents can recall specific past events — "last Tuesday you reported a billing issue" — rather than just general facts about the user. This enables proactive follow-up and contextual continuity across sessions.

## When to use it
- Support agents that need to reference prior complaints or commitments
- Assistants that should follow up on pending items from previous conversations
- Any workflow where the *sequence and timing* of events matters
- Building a timeline of what happened, not just what is generally true

## When NOT to use it
- Storing static preferences or facts (use semantic memory instead)
- Replacing a full audit log system — episodic memory is for agent context, not compliance
- High-volume event streams (millions of events per day) — consider a dedicated event store

## Architecture
- **Postgres**: durable store for all episodes, queried by `user_id` + `session_id`
- **Redis**: LRU-style cache of the last 20 events per user (`episodes:{user_id}` list), reduces Postgres reads on repeat queries

## Example
`example.py` runs two sessions for user `U42`:

- **Session 1**: user reports a billing issue; agent acknowledges and promises follow-up. Events saved to Postgres + Redis.
- **Session 2**: agent loads recent events from Redis cache, detects the prior billing complaint, and opens the conversation with a proactive follow-up — not a generic greeting.

```bash
# Start Postgres and Redis
docker-compose up -d

# Apply schema and run
cd 03-episodic-memory
python example.py
```

Watch for the `[cache]` log line that shows whether Redis or Postgres served the data.
