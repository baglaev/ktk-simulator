from asyncio import Queue
from uuid import UUID

from app.realtime import SessionSnapshotBroker, build_telemetry_update
from app.simulation import N1AProcessModel, load_n1a_model_profile
from app.scenarios import load_n1a_scenario


def initialized_model() -> N1AProcessModel:
    model = N1AProcessModel(load_n1a_scenario(), load_n1a_model_profile())
    model.initialize(UUID("11111111-1111-1111-1111-111111111111"))
    return model


def test_update_contains_complete_stable_component_list() -> None:
    model = initialized_model()
    previous = model.get_snapshot()
    current = model.step(10_000)

    update = build_telemetry_update(previous, current)

    assert update is not None
    assert update.type == "telemetry.update"
    assert update.sequence_no == current.sequence_no
    assert update.timing.elapsed_ms == 10_000
    assert [item.component_id for item in update.components] == [
        item.component_id for item in previous.components
    ]
    assert len(update.components) == 8


def test_update_is_empty_for_non_increasing_sequence() -> None:
    model = initialized_model()
    previous = model.get_snapshot()
    current = previous.model_copy(update={"state_version": 1})

    assert build_telemetry_update(previous, current) is None


def test_broker_fans_out_to_all_subscribers() -> None:
    model = initialized_model()
    snapshot = model.get_snapshot()
    broker = SessionSnapshotBroker()
    first = broker.subscribe(snapshot.session_id)
    second = broker.subscribe(snapshot.session_id)

    broker.publish(snapshot.session_id, snapshot)

    assert first.get_nowait() == snapshot
    assert second.get_nowait() == snapshot


def test_broker_keeps_latest_snapshot_for_slow_subscriber() -> None:
    model = initialized_model()
    broker = SessionSnapshotBroker(queue_size=1)
    queue: Queue = broker.subscribe(model.get_snapshot().session_id)
    first = model.get_snapshot()
    second = model.step(1_000)

    broker.publish(first.session_id, first)
    broker.publish(second.session_id, second)

    assert queue.get_nowait() == second
