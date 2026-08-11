from app.domain import (
    CreateSessionRequest,
    GeneralStatus,
    HintProvenance,
    ScenarioHintMessage,
    SessionResult,
    TrainingMode,
)
from sqlalchemy import inspect

from app.persistence import SessionRepository, create_database
from app.persistence.models import IssuedHintRecord
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


def test_legacy_fractional_result_parameters_are_rounded_on_read() -> None:
    _, factory = create_database("sqlite+pysqlite:///:memory:")
    manager = SessionManager(repository=SessionRepository(factory))
    created = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="legacy-trainee",
            mode=TrainingMode.TRAINING,
        )
    )
    manager.start_session(created.session_id)
    manager.advance_session(created.session_id, 120_000)
    payload = manager.get_result(created.session_id).model_dump(
        mode="json",
        by_alias=True,
    )
    payload["controlledParameters"][0]["finalValue"] = 4.8
    payload["controlledParameters"][0]["minimumValue"] = 99.636

    adopted = SessionResult.model_validate(payload)

    assert adopted.controlled_parameters[0].final_value == 5
    assert adopted.controlled_parameters[0].minimum_value == 100


def test_legacy_hint_mode_field_is_ignored_on_database_read() -> None:
    _, factory = create_database("sqlite+pysqlite:///:memory:")
    repository = SessionRepository(factory)
    session_id = "11111111-1111-1111-1111-111111111111"
    hint = ScenarioHintMessage(
        session_id=session_id,
        virtual_time_ms=10_000,
        hint_id="legacy-hint",
        level=GeneralStatus.WARNING,
        title="Проверка",
        message="Архивная подсказка",
        provenance=HintProvenance(source_refs=["учебное допущение"]),
    )
    repository.save_hint(hint)
    with factory.begin() as database:
        record = database.get(
            IssuedHintRecord,
            f"{session_id}:legacy-hint",
        )
        payload = dict(record.payload_json)
        payload["mode"] = "training"
        record.payload_json = payload

    hints = repository.list_hints(session_id)

    assert len(hints) == 1
    assert hints[0].hint_id == "legacy-hint"


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
