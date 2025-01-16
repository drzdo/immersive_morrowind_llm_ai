class Counter:
    def __init__(self) -> None:
        self._next = 1

    def get_next(self):
        v = self._next
        self._next = self._next + 1
        return v

    def reset(self):
        self._next = 1
