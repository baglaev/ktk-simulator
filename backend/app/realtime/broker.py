from __future__ import annotations

from asyncio import Queue, QueueEmpty, QueueFull
from threading import RLock
from uuid import UUID

from app.domain import ModelSnapshot, ScenarioHintMessage


RealtimeMessage = ModelSnapshot | ScenarioHintMessage


class SessionSnapshotBroker:
    """In-process fan-out broker for the single-worker MVP."""

    def __init__(self, queue_size: int = 32) -> None:
        self._queue_size = queue_size
        self._subscribers: dict[UUID, set[Queue[RealtimeMessage]]] = {}
        self._lock = RLock()

    def subscribe(self, session_id: UUID) -> Queue[RealtimeMessage]:
        queue: Queue[RealtimeMessage] = Queue(maxsize=self._queue_size)
        with self._lock:
            self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    def unsubscribe(
        self,
        session_id: UUID,
        queue: Queue[RealtimeMessage],
    ) -> None:
        with self._lock:
            session_subscribers = self._subscribers.get(session_id)
            if not session_subscribers:
                return
            session_subscribers.discard(queue)
            if not session_subscribers:
                self._subscribers.pop(session_id, None)

    def publish(self, session_id: UUID, snapshot: ModelSnapshot) -> None:
        self.publish_event(session_id, snapshot)

    def publish_event(self, session_id: UUID, event: RealtimeMessage) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers.get(session_id, ()))
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except QueueFull:
                try:
                    queue.get_nowait()
                except QueueEmpty:
                    pass
                queue.put_nowait(event)

    def subscriber_count(self, session_id: UUID) -> int:
        with self._lock:
            return len(self._subscribers.get(session_id, ()))
