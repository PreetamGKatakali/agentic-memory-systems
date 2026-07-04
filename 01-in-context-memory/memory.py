from collections import deque


class InContextMemory:
    def __init__(self, max_messages: int = 10):
        self._window: deque = deque(maxlen=max_messages)

    def add_message(self, role: str, content: str) -> None:
        self._window.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        return list(self._window)

    def size(self) -> int:
        return len(self._window)

    def max_size(self) -> int:
        return self._window.maxlen
