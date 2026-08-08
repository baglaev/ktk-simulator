from __future__ import annotations

from uuid import UUID, uuid5

from app.domain import (
    ActionType,
    ComponentParameterValue,
    ComponentState,
    EquipmentStatus,
    GeneralStatus,
    JournalEntry,
    ModelSnapshot,
    OperatorAction,
    ParameterOrigin,
    Provenance,
    ScenarioConfig,
    ScenarioTiming,
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
        self._equipment_definitions = {
            item.equipment_id: item for item in scenario.equipment
        }
        self._session_id: UUID | None = None
        self._elapsed_time_ms = 0
        self._sequence_no = 0
        self._state_version = 0
        self._journal: list[JournalEntry] = []

    def initialize(self, session_id: UUID) -> ModelSnapshot:
        self._session_id = session_id
        self._elapsed_time_ms = 0
        self._sequence_no = 0
        self._state_version = 0
        self._journal = self._journal_entries_between(-1, 0)
        return self.get_snapshot()

    def step(self, dt_ms: int) -> ModelSnapshot:
        self._require_initialized()
        if dt_ms <= 0:
            raise ValueError("dtMs must be greater than zero")
        if self._elapsed_time_ms >= self._profile.total_duration_ms:
            raise SimulationCompletedError("simulation has reached total duration")

        previous_time = self._elapsed_time_ms
        self._elapsed_time_ms = min(
            previous_time + dt_ms,
            self._profile.total_duration_ms,
        )
        self._sequence_no += 1
        self._state_version += 1
        self._journal.extend(
            self._journal_entries_between(previous_time, self._elapsed_time_ms)
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
        self._journal.append(
            JournalEntry(
                entry_id=action.action_id,
                time=_format_elapsed_time(self._elapsed_time_ms),
                description=self._describe_action(action),
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
            timing=self._timing(),
            components=self._component_states(),
            journal=list(self._journal),
        )

    def _timing(self) -> ScenarioTiming:
        total_ms = self._profile.total_duration_ms
        remaining_ms = max(total_ms - self._elapsed_time_ms, 0)
        return ScenarioTiming(
            elapsed_ms=self._elapsed_time_ms,
            total_ms=total_ms,
            remaining_ms=remaining_ms,
            progress_percent=round(self._elapsed_time_ms / total_ms * 100, 1),
        )

    def _component_states(self) -> list[ComponentState]:
        operating_timelines = {
            item.equipment_id: item for item in self._profile.equipment_statuses
        }
        status_timelines = {
            item.component_id: item for item in self._profile.component_statuses
        }
        raw_values = self._raw_signal_values()
        result: list[ComponentState] = []
        for component_id in self._profile.component_ids:
            definition = self._equipment_definitions[component_id]
            operating_timeline = operating_timelines.get(component_id)
            operating_state = (
                _step_value(
                    operating_timeline.keyframes,
                    self._elapsed_time_ms,
                    "status",
                )
                if operating_timeline
                else EquipmentStatus.UNKNOWN
            )
            component_status = _step_value(
                status_timelines[component_id].keyframes,
                self._elapsed_time_ms,
                "status",
            )
            state: dict[str, float] = {}
            if component_id == self._profile.fault.equipment_id:
                state["faultSeverityPercent"] = round(
                    _interpolate(
                        self._profile.fault.severity_keyframes,
                        self._elapsed_time_ms,
                    )
                    * 100,
                    1,
                )
            result.append(
                ComponentState(
                    component_id=component_id,
                    ui_id=_UI_IDS[component_id],
                    tag=definition.tag,
                    name=definition.name,
                    component_type=definition.equipment_type,
                    status=component_status,
                    operating_state=operating_state,
                    parameters=self._component_parameters(
                        component_id,
                        component_status,
                        raw_values,
                    ),
                    state=state,
                )
            )
        return result

    def _raw_signal_values(self) -> dict[str, float | int | bool | str | None]:
        values: dict[str, float | int | bool | str | None] = {}
        for trajectory in self._profile.numeric_trajectories:
            values[trajectory.signal_id] = _interpolate(
                trajectory.keyframes,
                self._elapsed_time_ms,
            )

        for trajectory in self._profile.discrete_trajectories:
            values[trajectory.signal_id] = _step_value(
                trajectory.keyframes,
                self._elapsed_time_ms,
                "value",
            )

        for static_signal in self._profile.static_signals:
            values[static_signal.signal_id] = static_signal.value

        return values

    def _component_parameters(
        self,
        component_id: str,
        status: GeneralStatus,
        raw_values: dict[str, float | int | bool | str | None],
    ) -> list[ComponentParameterValue]:
        result: list[ComponentParameterValue] = []
        for definition in self._scenario.signals:
            if definition.equipment_id != component_id:
                continue
            result.append(
                ComponentParameterValue(
                    parameter_id=definition.signal_id,
                    tag=definition.tag,
                    name=definition.name,
                    value_percent=self._to_percent(
                        definition.signal_id,
                        raw_values[definition.signal_id],
                    ),
                    status=status,
                )
            )
        return result

    def _to_percent(
        self,
        signal_id: str,
        raw_value: float | int | bool | str | None,
    ) -> float:
        if raw_value is None:
            raise ValueError(
                f"frontend parameter '{signal_id}' must have a percent value"
            )
        if isinstance(raw_value, bool):
            return 100.0 if raw_value else 0.0
        if not isinstance(raw_value, (float, int)):
            raise ValueError(f"signal '{signal_id}' cannot be converted to percent")

        definition = self._signal_definitions[signal_id]
        value = float(raw_value)
        if definition.unit != "percent_of_baseline":
            trajectory = next(
                item
                for item in self._profile.numeric_trajectories
                if item.signal_id == signal_id
            )
            baseline = trajectory.keyframes[0].value
            value = value / baseline * 100 if baseline else 0.0
        return round(value, definition.precision or 1)

    def _journal_entries_between(
        self,
        start_ms: int,
        end_ms: int,
    ) -> list[JournalEntry]:
        session_id = self._require_initialized()
        return [
            JournalEntry(
                entry_id=uuid5(
                    session_id,
                    f"{self._profile.model_id}:{item.event_key}",
                ),
                time=_format_elapsed_time(item.time_ms),
                description=item.description,
            )
            for item in self._profile.scheduled_events
            if start_ms < item.time_ms <= end_ms
        ]

    def _describe_action(self, action: OperatorAction) -> str:
        target = self._equipment_definitions.get(action.target_id)
        if target is not None:
            target_name = target.tag
        else:
            signal = self._signal_definitions.get(action.target_id)
            target_name = signal.tag if signal is not None else action.target_id
        template = _ACTION_DESCRIPTIONS[action.action_type]
        return template.format(target=target_name)

    def _require_initialized(self) -> UUID:
        if self._session_id is None:
            raise ModelNotInitializedError("model must be initialized first")
        return self._session_id

    def _validate_profile_references(self) -> None:
        if self._profile.scenario_id != self._scenario.scenario_id:
            raise ValueError("model profile belongs to another scenario")

        equipment_ids = {item.equipment_id for item in self._scenario.equipment}
        signal_ids = {item.signal_id for item in self._scenario.signals}
        if self._profile.component_ids != list(_UI_IDS):
            raise ValueError(
                "frontend component list or order differs from contract v2"
            )
        components_with_parameters = {
            item.equipment_id for item in self._scenario.signals
        }
        missing_parameters = set(self._profile.component_ids) - (
            components_with_parameters
        )
        if missing_parameters:
            raise ValueError(
                "frontend components without parameters: "
                f"{sorted(missing_parameters)}"
            )
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
        referenced_equipment.update(self._profile.component_ids)
        referenced_equipment.update(
            item.component_id for item in self._profile.component_statuses
        )
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
            item.provenance for item in self._profile.component_statuses
        )
        provenances.extend(
            item.provenance for item in self._profile.scheduled_events
        )
        for provenance in provenances:
            _validate_provenance(provenance, source_ids, assumption_ids)


_UI_IDS = {
    "eq-n1": "pump-h1",
    "eq-n1a": "pump-h1a",
    "eq-n1b": "pump-h1b",
    "eq-n1v": "pump-h1v",
    "eq-n1-discharge": "line-n1-elou",
    "eq-t1-t11": "heat-exchanger-t1-t11",
    "eq-elou": "elou-block",
    "eq-e15": "e15",
}


_ACTION_DESCRIPTIONS = {
    ActionType.OPEN_EQUIPMENT_CARD: "Открыта карточка компонента {target}",
    ActionType.VIEW_SIGNAL: "Просмотрен параметр {target}",
    ActionType.RUN_DIAGNOSTICS: "Запущена диагностика компонента {target}",
    ActionType.SUBMIT_DECISION: "Отправлено решение по компоненту {target}",
    ActionType.ACKNOWLEDGE_EVENT: "Подтверждено событие {target}",
}


def _format_elapsed_time(time_ms: int) -> str:
    total_seconds = time_ms // 1_000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


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
