from app.domain import ModelSnapshot, TelemetryUpdate


def build_telemetry_update(
    previous: ModelSnapshot,
    current: ModelSnapshot,
) -> TelemetryUpdate | None:
    """Build a full update with the same ordered component list every time."""

    if previous.session_id != current.session_id:
        raise ValueError("snapshots belong to different sessions")
    if previous.model_version != current.model_version:
        raise ValueError("snapshots use different model versions")
    if current.sequence_no <= previous.sequence_no:
        return None

    previous_ids = [item.component_id for item in previous.components]
    current_ids = [item.component_id for item in current.components]
    if current_ids != previous_ids:
        raise ValueError("frontend component list or order changed during session")

    return TelemetryUpdate(
        session_id=current.session_id,
        scenario_id=current.scenario_id,
        scenario_version=current.scenario_version,
        model_id=current.model_id,
        model_version=current.model_version,
        sequence_no=current.sequence_no,
        state_version=current.state_version,
        mode=current.mode,
        scenario_state=current.scenario_state,
        timing=current.timing,
        components=current.components,
        journal=current.journal,
    )
