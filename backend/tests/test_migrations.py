from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_adopts_pre_alembic_sqlite_schema(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE training_sessions (
                session_id VARCHAR(36) PRIMARY KEY NOT NULL,
                scenario_id VARCHAR(128) NOT NULL,
                scenario_version VARCHAR(32) NOT NULL,
                trainee_id VARCHAR(128) NOT NULL,
                instructor_id VARCHAR(128),
                mode VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
                elapsed_time_ms INTEGER NOT NULL,
                total_duration_ms INTEGER NOT NULL,
                state_version INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                started_at DATETIME,
                completed_at DATETIME
            )
            """
        )

    monkeypatch.setenv("KTK_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    try:
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()

    inspector = inspect(engine)
    columns = {
        item["name"]
        for item in inspector.get_columns("training_sessions")
    }
    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert {"model_id", "model_version"}.issubset(columns)
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "operator_actions",
        "session_results",
        "training_sessions",
    }
    assert revision == "20260810_01"
