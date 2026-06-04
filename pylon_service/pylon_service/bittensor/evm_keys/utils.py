import heapq


class UniqueMaxPriorityQueue:
    def __init__(self) -> None:
        self._heap: list[int] = []
        self._items: set[int] = set()

    def add(self, value: int) -> bool:
        if value in self._items:
            return False

        heapq.heappush(self._heap, -value)
        self._items.add(value)
        return True

    def pop_max(self) -> int:
        value = -heapq.heappop(self._heap)
        self._items.remove(value)
        return value

    def is_empty(self) -> bool:
        return not self._heap
