from functools import lru_cache

from app.realtime import SessionSnapshotBroker
from app.config import get_settings
from app.persistence import SessionRepository, create_database
from app.services import SessionManager


@lru_cache
def get_session_broker() -> SessionSnapshotBroker:
    return SessionSnapshotBroker()


@lru_cache
def get_session_manager() -> SessionManager:
    """One live-model manager; its audit trail is persisted in the database."""

    return SessionManager(
        snapshot_publisher=get_session_broker().publish,
        repository=get_session_repository(),
    )


@lru_cache
def get_session_repository() -> SessionRepository:
    _, session_factory = create_database(get_settings().database_url)
    return SessionRepository(session_factory)
