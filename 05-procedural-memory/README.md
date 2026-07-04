# 05 — Procedural Memory

## What it is
Stored, reusable multi-step routines persisted in Postgres. On first execution, the agent reasons through steps. On subsequent runs, it loads the stored procedure and replays it without re-planning — no Claude API call needed for planning.

## Why it's used
For recurring tasks, re-planning from scratch on every run wastes tokens and risks producing inconsistent step sequences. Procedural memory lets an agent build up a library of verified routines and reuse them reliably.

## When to use it
- Recurring workflows that follow the same steps each time (reports, data pipelines, onboarding flows)
- Situations where planning consistency matters more than flexibility
- Cost optimization: skip Claude for planning on known routines
- Workflows that need to be auditable — stored steps are inspectable in the DB

## When NOT to use it
- Tasks that require fresh reasoning each time due to changing inputs
- One-off operations not worth storing
- Highly dynamic environments where stored procedures would quickly become stale

## Example
`example.py` supports two modes:

**First run** — Claude reasons through steps for "Generate a weekly sales report", stores the procedure in Postgres:
```bash
cd 05-procedural-memory
python example.py --mode=first
```

**Replay run** — loads the stored procedure, replays steps without calling Claude for planning. Each step is tagged `[FROM STORED PROCEDURE]` vs `[FRESH REASONING]`:
```bash
python example.py --mode=replay
```

The difference is visible in the output: replay mode prints all steps as `FROM STORED PROCEDURE` and makes no Claude planning call. The `used_count` column in Postgres tracks how many times each procedure has been replayed.
