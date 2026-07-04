import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.claude_client import get_client, DEFAULT_MODEL
from memory import EpisodicMemory

USER_ID = "U42"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_memory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def apply_schema() -> None:
    import psycopg2

    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur, open(schema_path) as f:
        cur.execute(f.read())
    conn.close()


def session_1(mem: EpisodicMemory, client) -> str:
    session_id = str(uuid.uuid4())[:8]
    print("=" * 65)
    print(f"SESSION 1  (session_id={session_id})")
    print("=" * 65)

    exchanges = [
        ("user", "Hi, I'm having trouble with my invoice from last month. It charged me twice."),
        ("assistant", "I'm sorry to hear that. I've flagged the duplicate charge on your account and our billing team will review it within 24 hours. I'll follow up personally once resolved."),
        ("user", "Thank you. I hope it gets sorted out soon."),
        ("assistant", "Absolutely. I'll make sure to check back with you. Have a good day!"),
    ]

    for role, content in exchanges:
        mem.save_event(USER_ID, session_id, role, content)
        label = "User " if role == "user" else "Agent"
        print(f"  {label}: {content[:80]}")

    print(f"\nSaved {len(exchanges)} events for user {USER_ID}.\n")
    return session_id


def session_2(mem: EpisodicMemory, client, prior_session_id: str) -> None:
    session_id = str(uuid.uuid4())[:8]
    print("=" * 65)
    print(f"SESSION 2  (session_id={session_id}, later interaction)")
    print("=" * 65)

    recent = mem.get_recent_events(USER_ID)
    if not recent:
        print("No prior events found.")
        return

    history_text = "\n".join(
        f"[{e['role']}] {e['content']}" for e in recent
    )

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"You are a customer support agent. Here is your interaction history with user {USER_ID}:\n\n"
                    f"{history_text}\n\n"
                    f"The user has just reached out again. Open with a proactive follow-up on the specific past issue — "
                    f"not a generic greeting. Reference the actual issue."
                ),
            }
        ],
    )

    agent_opening = response.content[0].text
    mem.save_event(USER_ID, session_id, "assistant", agent_opening)

    print(f"\nAgent (opening from episodic recall):\n  {agent_opening}")


def main():
    apply_schema()
    client = get_client()
    mem = EpisodicMemory(DATABASE_URL, REDIS_URL)

    try:
        prior_session = session_1(mem, client)
        print("-" * 65)
        print("  [simulating a later session — same user, new interaction]")
        print("-" * 65, "\n")
        session_2(mem, client, prior_session)
    finally:
        mem.close()


if __name__ == "__main__":
    main()
