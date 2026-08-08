from functools import lru_cache

from app.realtime import SessionSnapshotBroker
from app.services import SessionManager


@lru_cache
def get_session_broker() -> SessionSnapshotBroker:
    return SessionSnapshotBroker()


@lru_cache
def get_session_manager() -> SessionManager:
    """One in-memory manager for the single-process MVP backend."""

    return SessionManager(snapshot_publisher=get_session_broker().publish)
