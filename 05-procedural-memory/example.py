import sys
import os
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.claude_client import get_client, DEFAULT_MODEL
from memory import ProceduralMemory

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_memory")
PROCEDURE_NAME = "weekly_sales_report"
TASK_DESCRIPTION = "Generate a weekly sales report"


def apply_schema() -> None:
    import psycopg2

    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur, open(schema_path) as f:
        cur.execute(f.read())
    conn.close()


def plan_steps_with_claude(client, task: str) -> list[dict]:
    prompt = (
        f"You are a planning agent. Break down this task into 4-5 concrete, executable steps:\n\n"
        f"Task: {task}\n\n"
        f"Return ONLY a JSON array of step objects with this exact shape:\n"
        f'[{{"step": 1, "action": "action_name", "description": "what this step does"}}]\n\n'
        f"No extra text, just the JSON array."
    )
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def execute_step(step: dict, source: str) -> None:
    tag = f"[{source}]"
    print(f"  {tag:25s} Step {step['step']}: {step['action']} — {step['description']}")


def run_first_mode(client, mem: ProceduralMemory) -> None:
    print("=" * 65)
    print("FIRST RUN — no stored procedure, agent plans from scratch")
    print("=" * 65)

    print(f"\nTask: {TASK_DESCRIPTION}")
    print("No stored procedure found. Asking Claude to plan steps...\n")

    steps = plan_steps_with_claude(client, TASK_DESCRIPTION)

    print("Claude reasoned through these steps:")
    for step in steps:
        execute_step(step, "FRESH REASONING")

    mem.store_procedure(
        name=PROCEDURE_NAME,
        description=TASK_DESCRIPTION,
        steps=steps,
    )
    print(f"\nProcedure '{PROCEDURE_NAME}' stored to Postgres ({len(steps)} steps).")
    print("Next run with --mode=replay will skip re-planning.\n")


def run_replay_mode(mem: ProceduralMemory) -> None:
    print("=" * 65)
    print("REPLAY RUN — loading stored procedure, skipping re-planning")
    print("=" * 65)

    print(f"\nTask: {TASK_DESCRIPTION}")

    steps = mem.load_procedure(PROCEDURE_NAME)
    if not steps:
        print(f"No stored procedure '{PROCEDURE_NAME}'. Run with --mode=first first.")
        return

    mem.increment_usage(PROCEDURE_NAME)
    print(f"Loaded {len(steps)} steps from Postgres. Replaying without Claude:\n")
    for step in steps:
        execute_step(step, "FROM STORED PROCEDURE")

    procedures = mem.list_procedures()
    usage = next((p["used_count"] for p in procedures if p["name"] == PROCEDURE_NAME), 0)
    print(f"\nProcedure '{PROCEDURE_NAME}' has now been replayed {usage} time(s).")
    print("No Claude API call was made — re-planning was avoided entirely.\n")


def main():
    parser = argparse.ArgumentParser(description="Procedural memory demo")
    parser.add_argument(
        "--mode",
        choices=["first", "replay"],
        default="first",
        help="'first' plans and stores; 'replay' loads and replays",
    )
    args = parser.parse_args()

    apply_schema()
    client = get_client()
    mem = ProceduralMemory(DATABASE_URL)

    try:
        if args.mode == "first":
            run_first_mode(client, mem)
        else:
            run_replay_mode(mem)
    finally:
        mem.close()


if __name__ == "__main__":
    main()
