from __future__ import annotations

from uuid import UUID, uuid5

from app.domain import (
    EquipmentState,
    EquipmentStatus,
    EventSeverity,
    ModelEvent,
    ModelSnapshot,
    OperatorAction,
    ParameterOrigin,
    Provenance,
    ScenarioConfig,
    SignalQuality,
    SignalValue,
)
from app.simulation.config import (
    ModelProfile,
    NumericKeyframe,
)


class ModelNotInitializedError(RuntimeError):
    pass


class StateVersionConflictError(RuntimeError):
    pass


class SimulationCompletedError(RuntimeError):
    pass


class N1AProcessModel:
    """Deterministic training model driven by versioned educational keyframes."""

    def __init__(self, scenario: ScenarioConfig, profile: ModelProfile) -> None:
        self._scenario = scenario
        self._profile = profile
        self._validate_profile_references()
        self._signal_definitions = {
            item.signal_id: item for item in scenario.signals
        }
        self._session_id: UUID | None = None
        self._virtual_time_ms = 0
        self._sequence_no = 0
        self._state_version = 0
        self._events: list[ModelEvent] = []

    def initialize(self, session_id: UUID) -> ModelSnapshot:
        self._session_id = session_id
        self._virtual_time_ms = 0
        self._sequence_no = 0
        self._state_version = 0
        self._events = self._events_between(-1, 0)
        return self.get_snapshot()

    def step(self, dt_ms: int) -> ModelSnapshot:
        self._require_initialized()
        if dt_ms <= 0:
            raise ValueError("dtMs must be greater than zero")
        if self._virtual_time_ms >= self._profile.max_virtual_time_ms:
            raise SimulationCompletedError("simulation has reached maxVirtualTimeMs")

        previous_time = self._virtual_time_ms
        self._virtual_time_ms = min(
            previous_time + dt_ms,
            self._profile.max_virtual_time_ms,
        )
        self._sequence_no += 1
        self._state_version += 1
        self._events.extend(
            self._events_between(previous_time, self._virtual_time_ms)
        )
        return self.get_snapshot()

    def apply_action(self, action: OperatorAction) -> ModelSnapshot:
        session_id = self._require_initialized()
        if action.session_id != session_id:
            raise ValueError("action belongs to another session")
        if action.expected_state_version != self._state_version:
            raise StateVersionConflictError(
                f"expected state version {self._state_version}, "
                f"got {action.expected_state_version}"
            )

        self._sequence_no += 1
        self._state_version += 1
        self._events.append(
            ModelEvent(
                event_id=action.action_id,
                event_type="operator_action_recorded",
                severity=EventSeverity.INFO,
                source_id=action.target_id,
                virtual_time_ms=self._virtual_time_ms,
                payload={
                    "actionType": action.action_type.value,
                    "targetId": action.target_id,
                },
            )
        )
        return self.get_snapshot()

    def get_snapshot(self) -> ModelSnapshot:
        session_id = self._require_initialized()
        return ModelSnapshot(
            session_id=session_id,
            scenario_id=self._scenario.scenario_id,
            scenario_version=self._scenario.scenario_version,
            model_id=self._profile.model_id,
            model_version=self._profile.model_version,
            sequence_no=self._sequence_no,
            state_version=self._state_version,
            virtual_time_ms=self._virtual_time_ms,
            equipment=self._equipment_states(),
            signals=self._signal_values(),
            events=list(self._events),
        )

    def _equipment_states(self) -> list[EquipmentState]:
        timelines = {
            item.equipment_id: item for item in self._profile.equipment_statuses
        }
        result: list[EquipmentState] = []
        for definition in self._scenario.equipment:
            timeline = timelines.get(definition.equipment_id)
            status = (
                _step_value(timeline.keyframes, self._virtual_time_ms, "status")
                if timeline
                else EquipmentStatus.UNKNOWN
            )
            state: dict[str, float | str] = {}
            if definition.equipment_id == self._profile.fault.equipment_id:
                state = {
                    "faultSeverity": _interpolate(
                        self._profile.fault.severity_keyframes,
                        self._virtual_time_ms,
                    ),
                    "diagnosticStatus": _step_value(
                        self._profile.fault.status_keyframes,
                        self._virtual_time_ms,
                        "status",
                    ),
                }
            result.append(
                EquipmentState(
                    equipment_id=definition.equipment_id,
                    status=status,
                    state=state,
                )
            )
        return result

    def _signal_values(self) -> list[SignalValue]:
        values: dict[str, SignalValue] = {}
        for trajectory in self._profile.numeric_trajectories:
            definition = self._signal_definitions[trajectory.signal_id]
            value = _interpolate(trajectory.keyframes, self._virtual_time_ms)
            if definition.precision is not None:
                value = round(value, definition.precision)
            values[trajectory.signal_id] = SignalValue(
                signal_id=trajectory.signal_id,
                value=value,
                quality=SignalQuality.GOOD,
                virtual_time_ms=self._virtual_time_ms,
            )

        for trajectory in self._profile.discrete_trajectories:
            values[trajectory.signal_id] = SignalValue(
                signal_id=trajectory.signal_id,
                value=_step_value(
                    trajectory.keyframes,
                    self._virtual_time_ms,
                    "value",
                ),
                quality=SignalQuality.GOOD,
                virtual_time_ms=self._virtual_time_ms,
            )

        for static_signal in self._profile.static_signals:
            values[static_signal.signal_id] = SignalValue(
                signal_id=static_signal.signal_id,
                value=static_signal.value,
                quality=static_signal.quality,
                virtual_time_ms=self._virtual_time_ms,
            )

        return [values[item.signal_id] for item in self._scenario.signals]

    def _events_between(self, start_ms: int, end_ms: int) -> list[ModelEvent]:
        session_id = self._require_initialized()
        return [
            ModelEvent(
                event_id=uuid5(
                    session_id,
                    f"{self._profile.model_id}:{item.event_key}",
                ),
                event_type=item.event_type,
                severity=item.severity,
                source_id=item.source_id,
                virtual_time_ms=item.time_ms,
                payload=item.payload,
            )
            for item in self._profile.scheduled_events
            if start_ms < item.time_ms <= end_ms
        ]

    def _require_initialized(self) -> UUID:
        if self._session_id is None:
            raise ModelNotInitializedError("model must be initialized first")
        return self._session_id

    def _validate_profile_references(self) -> None:
        if self._profile.scenario_id != self._scenario.scenario_id:
            raise ValueError("model profile belongs to another scenario")

        equipment_ids = {item.equipment_id for item in self._scenario.equipment}
        signal_ids = {item.signal_id for item in self._scenario.signals}
        configured_signal_ids = {
            item.signal_id for item in self._profile.numeric_trajectories
        }
        configured_signal_ids.update(
            item.signal_id for item in self._profile.discrete_trajectories
        )
        configured_signal_ids.update(
            item.signal_id for item in self._profile.static_signals
        )
        if configured_signal_ids != signal_ids:
            missing = sorted(signal_ids - configured_signal_ids)
            unknown = sorted(configured_signal_ids - signal_ids)
            raise ValueError(
                f"model signal coverage mismatch; missing={missing}, unknown={unknown}"
            )

        referenced_equipment = {
            item.equipment_id for item in self._profile.equipment_statuses
        }
        referenced_equipment.add(self._profile.fault.equipment_id)
        if not referenced_equipment.issubset(equipment_ids):
            raise ValueError("model profile references unknown equipment")

        source_ids = {item.source_ref_id for item in self._scenario.sources}
        assumption_ids = {
            item.assumption_id for item in self._scenario.assumptions
        }
        provenances = [self._profile.fault.provenance]
        provenances.extend(
            item.provenance for item in self._profile.numeric_trajectories
        )
        provenances.extend(
            item.provenance for item in self._profile.discrete_trajectories
        )
        provenances.extend(item.provenance for item in self._profile.static_signals)
        provenances.extend(
            item.provenance for item in self._profile.equipment_statuses
        )
        provenances.extend(
            item.provenance for item in self._profile.scheduled_events
        )
        for provenance in provenances:
            _validate_provenance(provenance, source_ids, assumption_ids)


def _interpolate(keyframes: list[NumericKeyframe], time_ms: int) -> float:
    if time_ms <= keyframes[0].time_ms:
        return keyframes[0].value
    if time_ms >= keyframes[-1].time_ms:
        return keyframes[-1].value

    for left, right in zip(keyframes, keyframes[1:]):
        if left.time_ms <= time_ms <= right.time_ms:
            fraction = (time_ms - left.time_ms) / (right.time_ms - left.time_ms)
            return left.value + fraction * (right.value - left.value)
    raise AssertionError("unreachable interpolation state")


def _step_value(keyframes: list[object], time_ms: int, field: str):
    value = getattr(keyframes[0], field)
    for item in keyframes:
        if getattr(item, "time_ms") > time_ms:
            break
        value = getattr(item, field)
    return value


def _validate_provenance(
    provenance: Provenance,
    source_ids: set[str],
    assumption_ids: set[str],
) -> None:
    if provenance.origin in {ParameterOrigin.SOURCE, ParameterOrigin.TEAM}:
        if provenance.source_ref_id not in source_ids:
            raise ValueError(
                f"unknown model source reference '{provenance.source_ref_id}'"
            )
    if provenance.origin is ParameterOrigin.EDUCATIONAL_ASSUMPTION:
        if provenance.assumption_id not in assumption_ids:
            raise ValueError(
                f"unknown model assumption '{provenance.assumption_id}'"
            )
