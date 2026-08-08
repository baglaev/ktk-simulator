import asyncio
from uuid import UUID

from app.domain import CreateSessionRequest, SessionStatus, TrainingMode
from app.services import SessionManager, SimulationRuntime


SESSION_ID = UUID("11111111-1111-1111-1111-111111111111")


def create_started_session() -> tuple[SessionManager, UUID]:
    manager = SessionManager(id_factory=lambda: SESSION_ID)
    session = manager.create_session(
        CreateSessionRequest(
            scenario_id="MVP-SC-01",
            trainee_id="trainee-001",
            mode=TrainingMode.TRAINING,
        )
    )
    manager.start_session(session.session_id)
    return manager, session.session_id


def test_runtime_advances_only_running_sessions() -> None:
    manager, session_id = create_started_session()
    runtime = SimulationRuntime(
        manager=manager,
        tick_interval_ms=1_000,
        step_ms=1_000,
    )

    runtime.tick_once()
    assert manager.get_session(session_id).virtual_time_ms == 1_000

    manager.pause_session(session_id)
    runtime.tick_once()
    assert manager.get_session(session_id).virtual_time_ms == 1_000

    manager.resume_session(session_id)
    runtime.tick_once()
    assert manager.get_session(session_id).virtual_time_ms == 2_000

    manager.complete_session(session_id)
    runtime.tick_once()
    assert manager.get_session(session_id).virtual_time_ms == 2_000


def test_runtime_completes_session_at_scenario_boundary() -> None:
    manager, session_id = create_started_session()
    runtime = SimulationRuntime(
        manager=manager,
        tick_interval_ms=1_000,
        step_ms=120_000,
    )

    runtime.tick_once()
    session = manager.get_session(session_id)

    assert session.virtual_time_ms == 120_000
    assert session.status is SessionStatus.COMPLETED
    assert session.completed_at is not None
    assert manager.running_session_ids() == ()


def test_background_runtime_starts_and_stops_cleanly() -> None:
    async def exercise() -> None:
        manager, session_id = create_started_session()
        runtime = SimulationRuntime(
            manager=manager,
            tick_interval_ms=5,
            step_ms=1_000,
        )

        await runtime.start()
        assert runtime.is_running
        for _ in range(20):
            if manager.get_session(session_id).virtual_time_ms > 0:
                break
            await asyncio.sleep(0.005)

        assert manager.get_session(session_id).virtual_time_ms > 0
        await runtime.stop()
        stopped_at = manager.get_session(session_id).virtual_time_ms
        assert not runtime.is_running

        await asyncio.sleep(0.015)
        assert manager.get_session(session_id).virtual_time_ms == stopped_at

    asyncio.run(exercise())


def test_runtime_start_is_idempotent() -> None:
    async def exercise() -> None:
        manager, _ = create_started_session()
        runtime = SimulationRuntime(
            manager=manager,
            tick_interval_ms=1_000,
            step_ms=1_000,
        )

        await runtime.start()
        first_task = runtime._task
        await runtime.start()
        assert runtime._task is first_task
        await runtime.stop()

    asyncio.run(exercise())
