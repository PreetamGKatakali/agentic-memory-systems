# 01 — In-Context Memory

## What it is
Conversation history stored directly in the prompt window passed to the model on each API call. No database, no external service — just a sliding list of recent messages capped at a fixed size.

## Why it's used
Zero infrastructure: the Claude API already accepts a `messages` list. It's the natural default for short, single-session conversations that don't need persistence.

## When to use it
- Short, self-contained conversations where forgetting old context is acceptable
- Prototyping or demos
- Stateless request/response flows
- Situations where the entire relevant history fits comfortably in the model's context window

## When NOT to use it
- Multi-session agents that need to remember users across restarts
- Long-running tasks where critical facts risk being pushed out of the window
- Any scenario where data must survive beyond the current process
- High-stakes workflows where silent forgetting would cause errors

## Example
`example.py` sets a 6-message window. The agent learns the user's name ("Alice") in turn 1, then handles 3 filler exchanges. By turn 5, the name has been pushed out of the window and the agent answers "I don't know" — even though it correctly used the name earlier.

```bash
cd 01-in-context-memory
python example.py
```

Expected output shows the window contents at each turn so you can watch "Alice" disappear.
