from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import Base


def create_database(
    database_url: str,
    *,
    initialize_schema: bool | None = None,
) -> tuple[Engine, sessionmaker[Session]]:
    """Create an engine; Alembic owns every persistent database schema.

    Ephemeral in-memory SQLite databases are initialized automatically for
    unit tests and isolated model instances. File-based SQLite and PostgreSQL
    must be migrated with ``alembic upgrade head`` before application start.
    """

    options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            from sqlalchemy.pool import StaticPool

            options["poolclass"] = StaticPool
    engine = create_engine(database_url, **options)
    if initialize_schema is None:
        initialize_schema = ":memory:" in database_url
    if initialize_schema:
        Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
