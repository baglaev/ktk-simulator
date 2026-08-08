from app.domain import ModelSnapshot, TelemetryDelta


def build_telemetry_delta(
    previous: ModelSnapshot,
    current: ModelSnapshot,
) -> TelemetryDelta | None:
    """Build a delta containing only changed values and newly emitted events."""

    if previous.session_id != current.session_id:
        raise ValueError("snapshots belong to different sessions")
    if previous.model_version != current.model_version:
        raise ValueError("snapshots use different model versions")

    previous_equipment = {
        item.equipment_id: item for item in previous.equipment
    }
    changed_equipment = [
        item
        for item in current.equipment
        if item.equipment_id not in previous_equipment
        or item.status != previous_equipment[item.equipment_id].status
        or item.state != previous_equipment[item.equipment_id].state
    ]

    previous_signals = {item.signal_id: item for item in previous.signals}
    changed_signals = [
        item
        for item in current.signals
        if item.signal_id not in previous_signals
        or item.value != previous_signals[item.signal_id].value
        or item.quality != previous_signals[item.signal_id].quality
    ]

    previous_event_ids = {item.event_id for item in previous.events}
    new_events = [
        item for item in current.events if item.event_id not in previous_event_ids
    ]

    if not (changed_equipment or changed_signals or new_events):
        return None

    return TelemetryDelta(
        session_id=current.session_id,
        scenario_id=current.scenario_id,
        scenario_version=current.scenario_version,
        model_id=current.model_id,
        model_version=current.model_version,
        sequence_no=current.sequence_no,
        state_version=current.state_version,
        virtual_time_ms=current.virtual_time_ms,
        equipment=changed_equipment,
        signals=changed_signals,
        events=new_events,
    )
