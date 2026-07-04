import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.claude_client import get_client, DEFAULT_MODEL
from memory import SemanticMemory

BACKEND = "pgvector" if os.getenv("USE_PGVECTOR", "false").lower() == "true" else "Pinecone"


def main():
    client = get_client()
    mem = SemanticMemory()

    print("=" * 65)
    print(f"SEMANTIC MEMORY DEMO  (backend: {BACKEND})")
    print("=" * 65)

    # Store facts — one preference, two unrelated fillers
    facts = [
        ("fact-units", "The user prefers metric units over imperial units.", {}),
        ("fact-food",  "The user is allergic to peanuts.", {"category": "health"}),
        ("fact-lang",  "The user's primary language is Spanish.", {"category": "language"}),
    ]

    print("\nStoring facts...")
    for fact_id, text, meta in facts:
        mem.store_fact(fact_id, text, meta)
        print(f"  stored [{fact_id}]: {text}")

    # Query with different wording — should surface the metric preference
    query = "What measurement system does this person like to use?"
    print(f"\nQuery: \"{query}\"")
    print("Retrieving top-3 by semantic similarity...\n")

    results = mem.retrieve_facts(query, top_k=3)
    for i, r in enumerate(results, 1):
        print(f"  #{i} (score={r['score']:.4f}) [{r['id']}]: {r['text']}")

    top_fact = results[0]["text"] if results else "No preference found."

    # Feed top preference to Claude for a concrete task
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=128,
        messages=[
            {
                "role": "user",
                "content": (
                    f"User preference: {top_fact}\n\n"
                    f"How far is it from London to Paris? Answer using the user's preferred unit system."
                ),
            }
        ],
    )

    print(f"\nClaude (applying retrieved preference):\n  {response.content[0].text}")
    print("\n" + "=" * 65)
    print(f"The agent applied the retrieved preference automatically.")
    print(f"Similarity matched '{results[0]['id']}' (score={results[0]['score']:.4f}) — not hard-coded.")
    print("=" * 65)

    mem.close()


if __name__ == "__main__":
    main()
