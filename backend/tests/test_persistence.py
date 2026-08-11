from app.domain import CreateSessionRequest, TrainingMode
from sqlalchemy import inspect

from app.persistence import SessionRepository, create_database
from app.services import SessionManager


def test_terminal_session_and_result_are_readable_by_new_manager() -> None:
    _, factory = create_database("sqlite+pysqlite:///:memory:")
    repository = SessionRepository(factory)
    first_manager = SessionManager(repository=repository)
    created = first_manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="persisted-trainee",
            mode=TrainingMode.TRAINING,
        )
    )
    first_manager.start_session(created.session_id)
    first_manager.advance_session(created.session_id, 120_000)

    second_manager = SessionManager(repository=repository)
    archived = second_manager.get_session(created.session_id)
    result = second_manager.get_result(created.session_id)

    assert archived.status.value == "failed"
    assert result.outcome.value == "failed"
    assert result.session_id == created.session_id


def test_in_memory_database_is_initialized_for_isolated_tests() -> None:
    engine, _ = create_database("sqlite+pysqlite:///:memory:")

    assert set(inspect(engine).get_table_names()) == {
        "issued_hints",
        "operator_actions",
        "session_ai_analyses",
        "session_results",
        "training_sessions",
    }


def test_persistent_database_schema_is_owned_by_alembic(tmp_path) -> None:
    database_path = tmp_path / "persistent.sqlite3"
    engine, _ = create_database(f"sqlite+pysqlite:///{database_path}")

    assert inspect(engine).get_table_names() == []
