import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.claude_client import get_client, DEFAULT_MODEL
from memory import ExternalMemory

CUSTOMER_ID = "C001"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_memory")


def apply_schema() -> None:
    import psycopg2

    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur, open(schema_path) as f:
        cur.execute(f.read())
    conn.close()


def session_a() -> None:
    print("=" * 65)
    print("SESSION A — writing order history to Postgres")
    print("=" * 65)

    mem = ExternalMemory(DATABASE_URL)
    orders = [
        ("Hiking boots", 1),
        ("Trail map pack", 3),
        ("Water filter", 2),
    ]
    for item, qty in orders:
        order_id = mem.add_order(CUSTOMER_ID, item, qty)
        print(f"  Inserted order #{order_id}: {qty}x {item}")
    mem.close()
    print("\nSession A complete. Connection closed.\n")


def session_b() -> None:
    print("=" * 65)
    print("SESSION B — fresh connection, reading back from Postgres")
    print("=" * 65)

    mem = ExternalMemory(DATABASE_URL)
    orders = mem.get_orders(CUSTOMER_ID)
    mem.close()

    if not orders:
        print("No orders found for customer", CUSTOMER_ID)
        return

    order_text = "\n".join(
        f"- Order #{o['id']}: {o['quantity']}x {o['item']} [{o['status']}] on {o['created_at'].strftime('%Y-%m-%d')}"
        for o in orders
    )
    print(f"  Loaded {len(orders)} orders from Postgres (no shared in-memory state):\n")
    print(order_text)

    client = get_client()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the order history for customer {CUSTOMER_ID}:\n\n"
                    f"{order_text}\n\n"
                    "Please give a one-sentence summary and flag any pending items."
                ),
            }
        ],
    )
    print(f"\nClaude summary:\n  {response.content[0].text}")


def main():
    apply_schema()
    session_a()
    print("-" * 65)
    print("  [process boundary — Session A has ended, connection closed]")
    print("-" * 65, "\n")
    session_b()


if __name__ == "__main__":
    main()
