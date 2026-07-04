import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common.claude_client import get_client, DEFAULT_MODEL
from memory import InContextMemory

MAX_MESSAGES = 6  # small window to make forgetting visible


def chat(client, memory: InContextMemory, user_msg: str) -> str:
    memory.add_message("user", user_msg)
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=128,
        messages=memory.get_messages(),
    )
    assistant_msg = response.content[0].text
    memory.add_message("assistant", assistant_msg)
    return assistant_msg


def print_window(memory: InContextMemory) -> None:
    print(f"  [Window: {memory.size()}/{memory.max_size()} messages]")
    for i, msg in enumerate(memory.get_messages()):
        preview = msg["content"][:70].replace("\n", " ")
        print(f"  [{i}] {msg['role']:9s}: {preview}")
    print()


def main():
    client = get_client()
    memory = InContextMemory(max_messages=MAX_MESSAGES)

    print("=" * 65)
    print(f"IN-CONTEXT MEMORY DEMO  (window = {MAX_MESSAGES} messages)")
    print("=" * 65)

    # Turn 1: plant a fact
    user_msg = "Hi! My name is Alice and I love hiking."
    reply = chat(client, memory, user_msg)
    print(f"\n[Turn 1] User: {user_msg}")
    print(f"         Asst: {reply}")
    print_window(memory)

    # Turns 2–4: filler exchanges to push Alice out of the window
    fillers = [
        "What is the capital of Japan?",
        "Tell me a fun fact about penguins.",
        "How many days are in a leap year?",
    ]
    for i, filler in enumerate(fillers, 2):
        reply = chat(client, memory, filler)
        print(f"[Turn {i}] User: {filler}")
        print(f"         Asst: {reply[:80]}...")
        print_window(memory)

    # Turn 5: ask for the forgotten fact
    user_msg = "What is my name?"
    reply = chat(client, memory, user_msg)
    print(f"[Turn 5] User: {user_msg}")
    print(f"         Asst: {reply}")
    print_window(memory)

    in_window = any(
        "alice" in msg["content"].lower() for msg in memory.get_messages()
    )
    print("=" * 65)
    print(f"'Alice' still in context window : {in_window}")
    print("The agent forgot the name because it slid out of the window.")
    print("=" * 65)


if __name__ == "__main__":
    main()
