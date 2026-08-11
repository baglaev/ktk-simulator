from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid5

from pydantic import JsonValue

from app.domain import (
    ActionErrorCode,
    ActionType,
    CompletionReason,
    ComponentParameterValue,
    ComponentState,
    DiagnosisConclusion,
    DiagnosisReason,
    EquipmentStatus,
    GeneralStatus,
    JournalEntry,
    ModelSnapshot,
    OperatorAction,
    ParameterOrigin,
    Provenance,
    RecordedAction,
    ScenarioConfig,
    ScenarioRuntimeState,
    ScenarioRuntimeStatus,
    ScenarioTiming,
    TrainingMode,
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
        self._mode = TrainingMode.TRAINING
        self._elapsed_time_ms = 0
        self._sequence_no = 0
        self._state_version = 0
        self._journal: list[JournalEntry] = []
        self._recorded_actions: list[RecordedAction] = []
        self._operating_states: dict[str, EquipmentStatus] = {}
        self._recovery_started_ms: int | None = None
        self._recovery_start_values: dict[str, float] = {}
        self._stabilized = False
        self._failure_reason: str | None = None
        self._completion_reason: CompletionReason | None = None
        self._min_lrca_605 = 65.0
        self._min_signal_values: dict[str, float] = {}

    def initialize(
        self,
        session_id: UUID,
        mode: TrainingMode = TrainingMode.TRAINING,
    ) -> ModelSnapshot:
        self._session_id = session_id
        self._mode = mode
        self._elapsed_time_ms = 0
        self._sequence_no = 0
        self._state_version = 0
        self._journal = self._journal_entries_between(-1, 0)
        self._recorded_actions = []
        self._operating_states = {
            item.equipment_id: _step_value(item.keyframes, 0, "status")
            for item in self._profile.equipment_statuses
        }
        self._recovery_started_ms = None
        self._recovery_start_values = {}
        self._stabilized = False
        self._failure_reason = None
        self._completion_reason = None
        self._min_lrca_605 = 65.0
        self._min_signal_values = {
            key: float(value)
            for key, value in self._raw_signal_values().items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        return self.get_snapshot()

    def step(self, dt_ms: int) -> ModelSnapshot:
        self._require_initialized()
        if dt_ms <= 0:
            raise ValueError("dtMs must be greater than zero")
        if self.is_terminal:
            raise SimulationCompletedError("simulation has reached a terminal state")

        previous_time = self._elapsed_time_ms
        boundary_ms = self._profile.total_duration_ms
        self._elapsed_time_ms = min(
            previous_time + dt_ms,
            boundary_ms,
        )
        self._sequence_no += 1
        self._state_version += 1
        self._journal.extend(
            self._journal_entries_between(previous_time, self._elapsed_time_ms)
        )
        raw_values = self._raw_signal_values()
        self._update_minimums(raw_values)
        self._min_lrca_605 = min(
            self._min_lrca_605,
            float(raw_values["LRCA605"]),
        )
        recovery_end_ms = (
            self._recovery_started_ms + _RECOVERY_DURATION_MS
            if self._recovery_started_ms is not None
            else None
        )
        if recovery_end_ms is not None and self._elapsed_time_ms >= recovery_end_ms:
            self._stabilized = True
            self._completion_reason = CompletionReason.OBJECTIVES_COMPLETED
            self._journal.append(
                self._system_journal_entry(
                    "recovery-completed",
                    self._elapsed_time_ms,
                    "Параметры стабилизированы после переключения на Н-1Б",
                )
            )
        elif float(raw_values["LRCA605"]) <= 20:
            self._failure_reason = "LRCA 605 достиг учебной границы 20%"
            self._completion_reason = CompletionReason.CRITICAL_LIMIT_REACHED
            self._journal.append(
                self._system_journal_entry(
                    "safety-limit-reached",
                    self._elapsed_time_ms,
                    "Сценарий завершён: LRCA 605 достиг учебной границы 20%",
                )
            )
        elif self._elapsed_time_ms >= self._profile.total_duration_ms:
            self._failure_reason = "Истекло максимальное учебное время сценария"
            self._completion_reason = CompletionReason.TIME_LIMIT_REACHED
            self._journal.append(
                self._system_journal_entry(
                    "time-limit-reached",
                    self._elapsed_time_ms,
                    "Сценарий завершён: истекло максимальное учебное время",
                )
            )
        return self.get_snapshot()

    def terminate_before_stabilization(self) -> ModelSnapshot:
        """Finalize a manual early completion as a failed training attempt."""

        self._require_initialized()
        if self.is_terminal:
            return self.get_snapshot()
        self._failure_reason = "Сценарий завершён до стабилизации параметров"
        self._completion_reason = CompletionReason.COMPLETED_BEFORE_STABILIZATION
        self._sequence_no += 1
        self._state_version += 1
        self._journal.append(
            self._system_journal_entry(
                "completed-before-stabilization",
                self._elapsed_time_ms,
                "Сценарий завершён пользователем до стабилизации параметров",
            )
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

        self._validate_action_target(action)
        errors = self._action_errors(action)
        self._apply_physical_action(action)
        self._update_recovery_state()

        self._sequence_no += 1
        self._state_version += 1
        description = self._describe_action(action)
        self._journal.append(
            JournalEntry(
                entry_id=action.action_id,
                time=_format_elapsed_time(self._elapsed_time_ms),
                description=description,
            )
        )
        self._recorded_actions.append(
            RecordedAction(
                action_id=action.action_id,
                session_id=session_id,
                sequence_no=self._sequence_no,
                virtual_time_ms=self._elapsed_time_ms,
                action_type=action.action_type,
                target_id=action.target_id,
                parameters=action.parameters,
                description=description,
                error_codes=errors,
                submitted_at=action.submitted_at,
            )
        )
        return self.get_snapshot()

    @property
    def is_stabilized(self) -> bool:
        return self._stabilized

    @property
    def is_failed(self) -> bool:
        return self._failure_reason is not None

    @property
    def is_terminal(self) -> bool:
        return self._stabilized or self.is_failed

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason

    @property
    def completion_reason(self) -> CompletionReason | None:
        return self._completion_reason

    @property
    def min_lrca_605(self) -> float:
        return self._min_lrca_605

    @property
    def min_signal_values(self) -> dict[str, float]:
        return dict(self._min_signal_values)

    def get_all_parameter_values(self) -> list[ComponentParameterValue]:
        """Return result-screen values even for a pump stopped by the trainee."""

        raw_values = self._raw_signal_values()
        status_timelines = {
            item.component_id: item for item in self._profile.component_statuses
        }
        result: list[ComponentParameterValue] = []
        for component_id in self._profile.component_ids:
            operating_state = self._operating_states.get(
                component_id,
                EquipmentStatus.UNKNOWN,
            )
            component_status = self._component_status(
                component_id,
                operating_state,
                raw_values,
                status_timelines,
            )
            result.extend(
                self._component_parameters(
                    component_id,
                    component_status,
                    raw_values,
                )
            )
        return result

    def get_recorded_actions(self) -> list[RecordedAction]:
        return [item.model_copy(deep=True) for item in self._recorded_actions]

    def record_hint(
        self,
        hint_id: str,
        title: str,
        message: str,
        virtual_time_ms: int,
    ) -> ModelSnapshot:
        """Add one prepared training hint to the persistent live journal."""

        self._require_initialized()
        entry = self._system_journal_entry(
            f"hint:{hint_id}",
            virtual_time_ms,
            f"Подсказка «{title}»: {message}",
        )
        if all(item.entry_id != entry.entry_id for item in self._journal):
            self._journal.append(entry)
        return self.get_snapshot()

    def has_safe_configuration(self) -> bool:
        return (
            self._operating_states.get("eq-n1b") is EquipmentStatus.RUNNING
            and self._operating_states.get("eq-n1a") is EquipmentStatus.STOPPED
            and self._operating_states.get("eq-n1") is EquipmentStatus.RUNNING
            and self._operating_states.get("eq-n1v") is EquipmentStatus.RUNNING
        )

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
            mode=self._mode,
            scenario_state=ScenarioRuntimeState(
                status=(
                    ScenarioRuntimeStatus.COMPLETED
                    if self.is_terminal
                    else ScenarioRuntimeStatus.ACTIVE
                ),
                completion_reason=self._completion_reason,
            ),
            timing=self._timing(),
            components=self._component_states(),
            journal=list(self._journal),
        )

    def _timing(self) -> ScenarioTiming:
        total_ms = self._profile.total_duration_ms
        remaining_ms = (
            0
            if self.is_terminal
            else max(total_ms - self._elapsed_time_ms, 0)
        )
        return ScenarioTiming(
            elapsed_ms=self._elapsed_time_ms,
            total_ms=total_ms,
            remaining_ms=remaining_ms,
            progress_percent=(
                100
                if self.is_terminal
                else min(
                    _round_display_value(self._elapsed_time_ms / total_ms * 100),
                    100,
                )
            ),
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
            operating_state = self._operating_states.get(
                component_id,
                _step_value(
                    operating_timeline.keyframes,
                    self._elapsed_time_ms,
                    "status",
                )
                if operating_timeline
                else EquipmentStatus.UNKNOWN,
            )
            component_status = self._component_status(
                component_id,
                operating_state,
                raw_values,
                status_timelines,
            )
            state: dict[str, JsonValue] = {}
            if component_id == self._profile.fault.equipment_id:
                state["faultSeverityPercent"] = _round_display_value(
                    _interpolate(
                        self._profile.fault.severity_keyframes,
                        self._elapsed_time_ms,
                    )
                    * 100
                )
            if component_id == "eq-n1-discharge":
                state.update(
                    {
                        "recoveryActive": self._recovery_started_ms is not None
                        and not self._stabilized,
                        "stabilized": self._stabilized,
                        "safePumpConfiguration": self.has_safe_configuration(),
                        "scenarioFailed": self.is_failed,
                        "failureReason": self._failure_reason,
                    }
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
                    parameters=(
                        []
                        if definition.equipment_type.value == "pump"
                        and operating_state is EquipmentStatus.STOPPED
                        else self._component_parameters(
                            component_id,
                            component_status,
                            raw_values,
                        )
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

        if self._recovery_started_ms is not None:
            fraction = min(
                max(
                    (self._elapsed_time_ms - self._recovery_started_ms)
                    / _RECOVERY_DURATION_MS,
                    0.0,
                ),
                1.0,
            )
            for signal_id, start_value in self._recovery_start_values.items():
                target = _RECOVERY_TARGETS[signal_id]
                values[signal_id] = start_value + fraction * (target - start_value)

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
                    measurement_type=definition.measurement_type,
                    value=self._frontend_value(
                        definition.signal_id, raw_values[definition.signal_id]
                    ),
                    unit=_DISPLAY_UNITS.get(definition.unit, definition.unit or "1"),
                    status=self._parameter_status(
                        definition.signal_id,
                        raw_values[definition.signal_id],
                        status,
                    ),
                )
            )
        return result

    def _frontend_value(
        self,
        signal_id: str,
        raw_value: float | int | bool | str | None,
    ) -> int:
        if raw_value is None:
            raise ValueError(f"frontend parameter '{signal_id}' has no value")
        if isinstance(raw_value, bool):
            return 100 if raw_value else 0
        if not isinstance(raw_value, (float, int)):
            raise ValueError(f"signal '{signal_id}' cannot be converted to percent")

        return _round_display_value(raw_value)

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
            and not (
                item.event_key in {
                    "line-decline",
                    "elou-decline",
                    "e15-decline",
                    "elou-low-level",
                    "critical-boundary",
                    "scenario-boundary",
                }
                and self._recovery_started_ms is not None
            )
            and not (
                item.source_id == "eq-n1a"
                and self._operating_states.get("eq-n1a") is EquipmentStatus.STOPPED
            )
        ]

    def _describe_action(self, action: OperatorAction) -> str:
        target = self._equipment_definitions.get(action.target_id)
        if target is not None:
            target_name = target.tag
        else:
            signal = self._signal_definitions.get(action.target_id)
            target_name = signal.tag if signal is not None else action.target_id
        if action.action_type is ActionType.SUBMIT_DIAGNOSIS:
            conclusion = DiagnosisConclusion(action.parameters["conclusion"])
            if conclusion is DiagnosisConclusion.NO_FAULT:
                return (
                    f"Диагноз {target_name}: "
                    f"{_DIAGNOSIS_CONCLUSIONS[conclusion]}"
                )
            reason = DiagnosisReason(action.parameters["reason"])
            return (
                f"Диагноз {target_name}: "
                f"{_DIAGNOSIS_CONCLUSIONS[conclusion]}, "
                f"причина — {_DIAGNOSIS_REASONS[reason]}"
            )
        template = _ACTION_DESCRIPTIONS[action.action_type]
        return template.format(target=target_name)

    def _apply_physical_action(self, action: OperatorAction) -> None:
        if action.action_type not in {ActionType.START_PUMP, ActionType.STOP_PUMP}:
            return
        if action.target_id not in _PUMP_IDS:
            raise ValueError(f"unknown pump '{action.target_id}'")
        self._operating_states[action.target_id] = (
            EquipmentStatus.RUNNING
            if action.action_type is ActionType.START_PUMP
            else EquipmentStatus.STOPPED
        )

    def _validate_action_target(self, action: OperatorAction) -> None:
        if action.action_type is ActionType.OPEN_EQUIPMENT_CARD:
            if action.target_id not in self._equipment_definitions:
                raise ValueError(f"unknown equipment '{action.target_id}'")
        elif action.action_type is ActionType.VIEW_SIGNAL:
            if action.target_id not in self._signal_definitions:
                raise ValueError(f"unknown signal '{action.target_id}'")
        elif action.action_type is ActionType.SUBMIT_DIAGNOSIS:
            if action.target_id not in _PUMP_IDS:
                raise ValueError(f"unknown pump '{action.target_id}'")
        elif action.action_type is ActionType.RUN_DIAGNOSTICS:
            if action.target_id != "eq-n1a":
                raise ValueError(
                    "run_diagnostics is available only for 'eq-n1a'"
                )

    def _update_recovery_state(self) -> None:
        if self.has_safe_configuration():
            if self._stabilized or self._recovery_started_ms is not None:
                return
            current = self._raw_signal_values()
            lrca = float(current["LRCA605"])
            self._min_lrca_605 = min(self._min_lrca_605, lrca)
            if lrca <= 20:
                self._failure_reason = "LRCA 605 достиг учебной границы 20%"
                return
            self._recovery_started_ms = self._elapsed_time_ms
            self._recovery_start_values = {
                signal_id: float(current[signal_id])
                for signal_id in _RECOVERY_TARGETS
            }
            self._journal.append(
                self._system_journal_entry(
                    "recovery-started",
                    self._elapsed_time_ms,
                    "Начато 30-секундное восстановление после безопасного переключения",
                )
            )
        elif self._recovery_started_ms is not None and not self._stabilized:
            self._recovery_started_ms = None
            self._recovery_start_values = {}
            self._journal.append(
                self._system_journal_entry(
                    "recovery-interrupted",
                    self._elapsed_time_ms,
                    "Восстановление прервано: конфигурация насосов небезопасна",
                )
            )

    def _action_errors(self, action: OperatorAction) -> list[ActionErrorCode]:
        errors: set[ActionErrorCode] = set()
        viewed = {
            item.target_id
            for item in self._recorded_actions
            if item.action_type is ActionType.VIEW_SIGNAL
        }
        diagnoses = [
            item
            for item in self._recorded_actions
            if item.action_type is ActionType.SUBMIT_DIAGNOSIS
        ]
        correct_diagnosis_exists = any(
            _is_correct_diagnosis(item) for item in diagnoses
        )

        if action.action_type is ActionType.SUBMIT_DIAGNOSIS:
            conclusion = DiagnosisConclusion(action.parameters["conclusion"])
            reason_value = action.parameters.get("reason")
            reason = (
                DiagnosisReason(reason_value)
                if reason_value is not None
                else None
            )
            if action.target_id != "eq-n1a":
                errors.add(ActionErrorCode.HEALTHY_PUMP_SELECTED)
            if conclusion is not DiagnosisConclusion.FAULT_DETECTED:
                errors.add(ActionErrorCode.FAULT_NOT_DETECTED)
            if reason is not DiagnosisReason.BEARING_WEAR:
                errors.add(ActionErrorCode.WRONG_DIAGNOSIS_REASON)
            if self._elapsed_time_ms > 80_000:
                errors.add(ActionErrorCode.DIAGNOSIS_TOO_LATE)
            if "PRA351" not in viewed:
                errors.add(ActionErrorCode.DIAGNOSIS_WITHOUT_PRA_CHECK)
            if "FYQR117" not in viewed:
                errors.add(ActionErrorCode.DIAGNOSIS_WITHOUT_FYQR_CHECK)
            if diagnoses and _is_correct_action_diagnosis(action):
                if any(not _is_correct_diagnosis(item) for item in diagnoses):
                    errors.add(ActionErrorCode.WRONG_DIAGNOSIS_CORRECTED)

        if action.action_type in {ActionType.START_PUMP, ActionType.STOP_PUMP}:
            if not correct_diagnosis_exists:
                errors.add(ActionErrorCode.SWITCH_BEFORE_DIAGNOSIS)
            if self._elapsed_time_ms < 10_000:
                errors.add(ActionErrorCode.PUMP_COMMAND_BEFORE_WARNING)
            if action.action_type is ActionType.STOP_PUMP:
                if action.target_id != "eq-n1a":
                    errors.add(ActionErrorCode.HEALTHY_PUMP_STOPPED)
                if action.target_id == "eq-n1a":
                    if (
                        self._operating_states.get("eq-n1b")
                        is not EquipmentStatus.RUNNING
                    ):
                        errors.add(ActionErrorCode.N1A_STOPPED_BEFORE_N1B)
                    if not correct_diagnosis_exists:
                        errors.add(ActionErrorCode.N1A_STOPPED_WITHOUT_DIAGNOSIS)
                if action.target_id == "eq-n1b" and any(
                    item.action_type is ActionType.START_PUMP
                    and item.target_id == "eq-n1b"
                    for item in self._recorded_actions
                ):
                    errors.add(ActionErrorCode.N1B_STOPPED_AFTER_START)
            if (
                action.action_type is ActionType.START_PUMP
                and action.target_id == "eq-n1a"
                and any(
                    item.action_type is ActionType.STOP_PUMP
                    and item.target_id == "eq-n1a"
                    for item in self._recorded_actions
                )
            ):
                errors.add(ActionErrorCode.N1A_RESTARTED_AFTER_SWITCH)
            if self._operating_states.get(action.target_id) is (
                EquipmentStatus.RUNNING
                if action.action_type is ActionType.START_PUMP
                else EquipmentStatus.STOPPED
            ):
                errors.add(ActionErrorCode.UNNECESSARY_REPEATED_SWITCHING)
            prospective = dict(self._operating_states)
            prospective[action.target_id] = (
                EquipmentStatus.RUNNING
                if action.action_type is ActionType.START_PUMP
                else EquipmentStatus.STOPPED
            )
            if sum(
                prospective.get(pump_id) is EquipmentStatus.STOPPED
                for pump_id in _PUMP_IDS
            ) > 1:
                errors.add(ActionErrorCode.MULTIPLE_PUMPS_STOPPED)
        return sorted(errors, key=lambda item: item.value)

    def _component_status(
        self,
        component_id: str,
        operating_state: EquipmentStatus,
        raw_values: dict[str, float | int | bool | str | None],
        timelines: dict[str, object],
    ) -> GeneralStatus:
        if operating_state is EquipmentStatus.STOPPED:
            return GeneralStatus.SUCCESS
        if component_id == "eq-n1-discharge":
            value = min(
                float(raw_values["PRA351"]),
                float(raw_values["FYQR117"]),
            )
            return _low_value_status(value, 80, 95)
        if component_id == "eq-t1-t11":
            return _low_value_status(float(raw_values["T1T11.FLOW"]), 70, 95)
        if component_id == "eq-elou":
            value = min(
                float(raw_values["ELOU.STAGE1.LEVEL"]),
                float(raw_values["ELOU.STAGE2.LEVEL"]),
            )
            return _low_value_status(value, 80, 95)
        if component_id == "eq-e15":
            return _low_value_status(float(raw_values["LRCA605"]), 30, 60)
        return _step_value(
            timelines[component_id].keyframes,
            self._elapsed_time_ms,
            "status",
        )

    def _parameter_status(
        self,
        signal_id: str,
        raw_value: float | int | bool | str | None,
        fallback: GeneralStatus,
    ) -> GeneralStatus:
        if not signal_id.startswith("COMPAX.") or not isinstance(
            raw_value,
            (int, float),
        ):
            return fallback
        metric = signal_id.rsplit(".", 1)[-1]
        warning, alert = _COMPAX_THRESHOLDS[metric]
        if float(raw_value) >= alert:
            return GeneralStatus.ALERT
        if float(raw_value) >= warning:
            return GeneralStatus.WARNING
        return GeneralStatus.SUCCESS

    def _system_journal_entry(
        self,
        event_key: str,
        time_ms: int,
        description: str,
    ) -> JournalEntry:
        session_id = self._require_initialized()
        return JournalEntry(
            entry_id=uuid5(
                session_id,
                f"{self._profile.model_id}:{event_key}:{time_ms}",
            ),
            time=_format_elapsed_time(time_ms),
            description=description,
        )

    def _update_minimums(
        self,
        values: dict[str, float | int | bool | str | None],
    ) -> None:
        for signal_id, value in values.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            numeric = float(value)
            self._min_signal_values[signal_id] = min(
                self._min_signal_values.get(signal_id, numeric),
                numeric,
            )

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
                "frontend component list or order differs from contract v3"
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
    ActionType.START_PUMP: "Запущен насос {target}",
    ActionType.STOP_PUMP: "Остановлен насос {target}",
}


_PUMP_IDS = {"eq-n1", "eq-n1a", "eq-n1b", "eq-n1v"}
# Учебное допущение A-17 из model-definition, не производственная уставка.
_RECOVERY_DURATION_MS = 30_000
_RECOVERY_TARGETS = {
    "PRA351": 100.0,
    "FYQR117": 100.0,
    "ELOU.STAGE1.LEVEL": 100.0,
    "ELOU.STAGE2.LEVEL": 100.0,
    "LRCA605": 65.0,
}
# Учебная методика A-18 из model-definition.
_COMPAX_THRESHOLDS = {
    "TEMPERATURE": (75.0, 90.0),
    "VELOCITY": (4.5, 7.1),
    "ACCELERATION": (15.0, 30.0),
    "DISPLACEMENT": (80.0, 160.0),
    "CURRENT": (105.0, 115.0),
}
_DISPLAY_UNITS = {
    "degC": "°C",
    "mm/s": "мм/с",
    "m/s2": "м/с²",
    "um": "мкм",
    "percent_of_baseline": "%",
}
_DIAGNOSIS_CONCLUSIONS = {
    DiagnosisConclusion.FAULT_DETECTED: "неисправность выявлена",
    DiagnosisConclusion.NO_FAULT: "неисправность не выявлена",
}
_DIAGNOSIS_REASONS = {
    DiagnosisReason.BEARING_WEAR: "развивающийся износ подшипника",
    DiagnosisReason.CAVITATION: "кавитация",
    DiagnosisReason.ELECTRICAL_OVERLOAD: "электрическая перегрузка",
    DiagnosisReason.SUCTION_SUPPLY_DISRUPTION: (
        "нарушение подачи на всасывающей линии"
    ),
    DiagnosisReason.COMPAX_SENSOR_FAULT: "неисправность датчика системы КОМПАКС",
    DiagnosisReason.UNKNOWN: "причина не определена",
}


def _is_correct_action_diagnosis(action: OperatorAction) -> bool:
    return (
        action.target_id == "eq-n1a"
        and action.parameters.get("conclusion")
        == DiagnosisConclusion.FAULT_DETECTED.value
        and action.parameters.get("reason") == DiagnosisReason.BEARING_WEAR.value
    )


def _is_correct_diagnosis(action: RecordedAction) -> bool:
    return (
        action.target_id == "eq-n1a"
        and action.parameters.get("conclusion")
        == DiagnosisConclusion.FAULT_DETECTED.value
        and action.parameters.get("reason") == DiagnosisReason.BEARING_WEAR.value
    )


def _low_value_status(
    value: float,
    alert_at: float,
    warning_at: float,
) -> GeneralStatus:
    if value <= alert_at:
        return GeneralStatus.ALERT
    if value < warning_at:
        return GeneralStatus.WARNING
    return GeneralStatus.SUCCESS


def _format_elapsed_time(time_ms: int) -> str:
    total_seconds = time_ms // 1_000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _round_display_value(value: float | int) -> int:
    """Round a non-negative model value for the public UI contract."""

    return int(
        Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


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
