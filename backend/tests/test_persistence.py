from app.domain import CreateSessionRequest, TrainingMode
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
