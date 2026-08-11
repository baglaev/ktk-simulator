from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from app.domain import (
    ActionErrorCode,
    ActionType,
    DiagnosisConclusion,
    DiagnosisReason,
    CompletionReason,
    ComponentParameterValue,
    GeneralStatus,
    ModelSnapshot,
    RecordedAction,
    ResultParameter,
    ResultRemark,
    ResultStatus,
    ScenarioOutcome,
    ScoreSection,
    SessionResult,
    TaskExecutionItem,
    TrainingMode,
)


def evaluate_session(
    *,
    session_id: UUID,
    actions: list[RecordedAction],
    completed_at: datetime,
    safe_configuration: bool,
    stabilized: bool,
    min_lrca_605: float,
    model_failure_reason: str | None = None,
    mode: TrainingMode = TrainingMode.TRAINING,
    completion_reason: CompletionReason = CompletionReason.COMPLETED_BEFORE_STABILIZATION,
    snapshot: ModelSnapshot | None = None,
    minimum_values: dict[str, float] | None = None,
    final_parameters: list[ComponentParameterValue] | None = None,
) -> SessionResult:
    """Apply deterministic SCR-04 rubric (educational assumption A-18)."""

    diagnoses = [
        item for item in actions if item.action_type is ActionType.SUBMIT_DIAGNOSIS
    ]
    correct_diagnoses = [item for item in diagnoses if _correct_diagnosis(item)]
    identified_fault = [item for item in diagnoses if _identifies_fault(item)]
    first_diagnosis = diagnoses[0] if diagnoses else None
    first_correct = correct_diagnoses[0] if correct_diagnoses else None
    first_pump_action = _first(
        item
        for item in actions
        if item.action_type in {ActionType.START_PUMP, ActionType.STOP_PUMP}
    )
    start_n1b = _first(
        item
        for item in actions
        if item.action_type is ActionType.START_PUMP and item.target_id == "eq-n1b"
    )
    stop_n1a = _first(
        item
        for item in actions
        if item.action_type is ActionType.STOP_PUMP and item.target_id == "eq-n1a"
    )
    switch_time = (
        max(start_n1b.virtual_time_ms, stop_n1a.virtual_time_ms)
        if start_n1b is not None and stop_n1a is not None
        else None
    )

    diagnosis_score = 0
    if _has_action(
        actions,
        ActionType.OPEN_EQUIPMENT_CARD,
        "eq-n1a",
        at_or_after=10_000,
    ):
        diagnosis_score += 3
    if first_diagnosis is not None:
        if _has_action(
            actions,
            ActionType.VIEW_SIGNAL,
            "PRA351",
            before=first_diagnosis.virtual_time_ms,
        ):
            diagnosis_score += 3
        if _has_action(
            actions,
            ActionType.VIEW_SIGNAL,
            "FYQR117",
            before=first_diagnosis.virtual_time_ms,
        ):
            diagnosis_score += 3
    if first_correct is not None:
        if first_diagnosis is first_correct:
            diagnosis_score += 16
        elif first_diagnosis is not None and _identifies_fault(first_diagnosis):
            # The faulty unit was identified immediately, but the reason was
            # corrected later: full 9 points for the unit and half for reason.
            diagnosis_score += 12
        else:
            diagnosis_score += 8
    elif identified_fault:
        diagnosis_score += 9 if identified_fault[0] is first_diagnosis else 4

    stabilization_score = 0
    if (
        first_correct is not None
        and (
            first_pump_action is None
            or first_correct.sequence_no < first_pump_action.sequence_no
        )
    ):
        stabilization_score += 5
    if start_n1b is not None:
        stabilization_score += 10
    if stop_n1a is not None:
        stabilization_score += 10
    if (
        start_n1b is not None
        and stop_n1a is not None
        and start_n1b.sequence_no < stop_n1a.sequence_no
    ):
        stabilization_score += 15

    consequence_score = 0
    if switch_time is not None:
        if _has_action(
            actions,
            ActionType.VIEW_SIGNAL,
            "PRA351",
            after=switch_time,
        ):
            consequence_score += 2
        if _has_action(
            actions,
            ActionType.VIEW_SIGNAL,
            "FYQR117",
            after=switch_time,
        ):
            consequence_score += 2
        if _checked_component(actions, "eq-elou", switch_time):
            consequence_score += 4
        if _checked_component(actions, "eq-e15", switch_time):
            consequence_score += 5
    if safe_configuration and stabilized:
        consequence_score += 4
    if min_lrca_605 > 20:
        consequence_score += 3

    timeliness_score = 0
    if switch_time is not None:
        if switch_time <= 80_000:
            timeliness_score = 15
        elif switch_time <= 110_000:
            timeliness_score = 7

    all_errors = {code for item in actions for code in item.error_codes}
    if not diagnoses:
        all_errors.add(ActionErrorCode.WARNING_IGNORED)
    elif not _has_action(actions, ActionType.RUN_DIAGNOSTICS, "eq-n1a"):
        all_errors.add(ActionErrorCode.DIAGNOSTICS_NOT_RUN)
    if not _has_action(actions, ActionType.VIEW_SIGNAL, "PRA351"):
        all_errors.add(ActionErrorCode.PRA_NOT_CHECKED)
    if not _has_action(actions, ActionType.VIEW_SIGNAL, "FYQR117"):
        all_errors.add(ActionErrorCode.FYQR_NOT_CHECKED)
    if switch_time is not None and not _checked_component(
        actions,
        "eq-elou",
        switch_time,
    ):
        all_errors.add(ActionErrorCode.ELOU_NOT_CHECKED_AFTER_SWITCH)
    if switch_time is not None and not _checked_component(
        actions,
        "eq-e15",
        switch_time,
    ):
        all_errors.add(ActionErrorCode.E15_NOT_CHECKED_AFTER_SWITCH)
    if switch_time is not None and not _has_action(
        actions,
        ActionType.VIEW_SIGNAL,
        "LRCA605",
        after=switch_time,
    ):
        all_errors.add(ActionErrorCode.LRCA_RECOVERY_NOT_CONFIRMED)
    if not stabilized:
        all_errors.add(ActionErrorCode.COMPLETED_BEFORE_STABLE)
    if min_lrca_605 <= 20:
        all_errors.add(ActionErrorCode.E15_SAFETY_LIMIT_REACHED)
    if start_n1b is not None and stop_n1a is None:
        all_errors.add(ActionErrorCode.N1A_LEFT_RUNNING)

    stopped_pumps = {
        item.target_id
        for item in actions
        if item.action_type is ActionType.STOP_PUMP
        and item.target_id in {"eq-n1", "eq-n1a", "eq-n1b", "eq-n1v"}
    }
    if len(stopped_pumps) > 1:
        all_errors.add(ActionErrorCode.MULTIPLE_PUMPS_STOPPED)

    penalties = 0
    if ActionErrorCode.HEALTHY_PUMP_STOPPED in all_errors:
        penalties -= 10
    if ActionErrorCode.N1B_STOPPED_AFTER_START in all_errors:
        penalties -= 5
    if ActionErrorCode.PUMP_COMMAND_BEFORE_WARNING in all_errors:
        penalties -= 5
    if ActionErrorCode.N1A_RESTARTED_AFTER_SWITCH in all_errors:
        penalties -= 5

    critical_reasons: list[str] = []
    if min_lrca_605 <= 20:
        critical_reasons.append("LRCA 605 достиг учебной границы 20%")
    if not safe_configuration:
        critical_reasons.append("Сценарий завершён без безопасной конфигурации насосов")
    if not stabilized:
        critical_reasons.append("Сценарий завершён до стабилизации параметров")
    if first_correct is None:
        critical_reasons.append("Корректный учебный диагноз Н-1А не зафиксирован")
    if model_failure_reason and model_failure_reason not in critical_reasons:
        critical_reasons.append(model_failure_reason)

    total = max(
        0,
        min(
            100,
            diagnosis_score
            + stabilization_score
            + consequence_score
            + timeliness_score
            + penalties,
        ),
    )
    result_status = (
        ResultStatus.FAILED
        if critical_reasons
        else ResultStatus.PASSED_WITH_REMARKS
        if all_errors
        else ResultStatus.PASSED
    )
    task_execution = _task_execution(
        first_correct=first_correct,
        start_n1b=start_n1b,
        stop_n1a=stop_n1a,
        switch_time=switch_time,
        stabilized=stabilized,
        actions=actions,
    )
    remarks = _remarks(all_errors, critical_reasons)
    return SessionResult(
        session_id=session_id,
        status=result_status,
        outcome=(
            ScenarioOutcome.FAILED
            if result_status is ResultStatus.FAILED
            else ScenarioOutcome.SUCCESS
        ),
        mode=mode,
        completion_reason=completion_reason,
        summary=_summary(result_status, total, completed_at),
        elapsed_time_ms=snapshot.timing.elapsed_ms if snapshot is not None else 0,
        total_score=total,
        diagnosis=ScoreSection(score=diagnosis_score, max_score=25),
        stabilization=ScoreSection(score=stabilization_score, max_score=40),
        consequence_control=ScoreSection(score=consequence_score, max_score=20),
        timeliness=ScoreSection(score=timeliness_score, max_score=15),
        penalties=penalties,
        error_codes=sorted(all_errors, key=lambda item: item.value),
        critical_failure_reasons=critical_reasons,
        task_execution=task_execution,
        controlled_parameters=_controlled_parameters(
            snapshot,
            minimum_values or {"LRCA605": min_lrca_605},
            final_parameters,
        ),
        remarks=remarks,
        completed_at=completed_at,
    )


def _task_execution(
    *,
    first_correct: RecordedAction | None,
    start_n1b: RecordedAction | None,
    stop_n1a: RecordedAction | None,
    switch_time: int | None,
    stabilized: bool,
    actions: list[RecordedAction],
) -> list[TaskExecutionItem]:
    diagnosis_status = GeneralStatus.SUCCESS if first_correct else GeneralStatus.ALERT
    correct_order = (
        start_n1b is not None
        and stop_n1a is not None
        and start_n1b.sequence_no < stop_n1a.sequence_no
    )
    switching_status = (
        GeneralStatus.SUCCESS
        if correct_order
        else GeneralStatus.WARNING
        if start_n1b is not None or stop_n1a is not None
        else GeneralStatus.ALERT
    )
    consequence_targets = {
        (ActionType.VIEW_SIGNAL, "PRA351"),
        (ActionType.VIEW_SIGNAL, "FYQR117"),
        (ActionType.OPEN_EQUIPMENT_CARD, "eq-elou"),
        (ActionType.OPEN_EQUIPMENT_CARD, "eq-e15"),
        (ActionType.VIEW_SIGNAL, "LRCA605"),
    }
    checked = {
        (item.action_type, item.target_id)
        for item in actions
        if switch_time is not None and item.virtual_time_ms >= switch_time
    }
    recovery_status = (
        GeneralStatus.SUCCESS
        if stabilized and consequence_targets.issubset(checked)
        else GeneralStatus.WARNING
        if stabilized
        else GeneralStatus.ALERT
    )
    return [
        TaskExecutionItem(
            task_id="diagnosis",
            title="Диагностика Н-1А",
            status=diagnosis_status,
            completed_at_ms=(first_correct.virtual_time_ms if first_correct else None),
            description=(
                "Корректный учебный диагноз зафиксирован"
                if first_correct
                else "Корректный учебный диагноз не зафиксирован"
            ),
        ),
        TaskExecutionItem(
            task_id="pump_switch",
            title="Переключение насосов",
            status=switching_status,
            completed_at_ms=switch_time,
            description=(
                "Н-1Б запущен до остановки Н-1А"
                if correct_order
                else "Последовательность переключения выполнена не полностью"
            ),
        ),
        TaskExecutionItem(
            task_id="recovery_control",
            title="Контроль восстановления",
            status=recovery_status,
            completed_at_ms=(
                max((item.virtual_time_ms for item in actions), default=None)
                if stabilized
                else None
            ),
            description=(
                "Учебная модель стабилизирована"
                if stabilized
                else "Стабилизация учебной модели не подтверждена"
            ),
        ),
    ]


def _controlled_parameters(
    snapshot: ModelSnapshot | None,
    minimum_values: dict[str, float],
    final_parameters: list[ComponentParameterValue] | None,
) -> list[ResultParameter]:
    if snapshot is None and final_parameters is None:
        return []
    controlled_ids = {
        "PRA351",
        "FYQR117",
        "ELOU.STAGE1.LEVEL",
        "ELOU.STAGE2.LEVEL",
        "LRCA605",
        "COMPAX.N1A.TEMPERATURE",
        "COMPAX.N1A.VELOCITY",
        "COMPAX.N1A.ACCELERATION",
        "COMPAX.N1A.DISPLACEMENT",
        "COMPAX.N1A.CURRENT",
    }
    parameters = final_parameters or [
        parameter
        for component in snapshot.components  # type: ignore[union-attr]
        for parameter in component.parameters
    ]
    return [
        ResultParameter(
            parameter_id=parameter.parameter_id,
            name=parameter.name,
            final_value=parameter.value,
            minimum_value=int(
                Decimal(
                    str(
                        minimum_values.get(
                            parameter.parameter_id,
                            parameter.value,
                        )
                    )
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            ),
            unit=parameter.unit,
            status=parameter.status,
        )
        for parameter in parameters
        if parameter.parameter_id in controlled_ids
    ]


def _remarks(
    errors: set[ActionErrorCode],
    critical_reasons: list[str],
) -> list[ResultRemark]:
    result = [
        ResultRemark(
            code=f"critical-{index}",
            status=GeneralStatus.ALERT,
            title="Критическое условие",
            description=description,
        )
        for index, description in enumerate(critical_reasons, start=1)
    ]
    critical_error_codes = {
        ActionErrorCode.E15_SAFETY_LIMIT_REACHED,
        ActionErrorCode.COMPLETED_BEFORE_STABLE,
        ActionErrorCode.MULTIPLE_PUMPS_STOPPED,
    }
    for error in sorted(errors, key=lambda item: item.value):
        result.append(
            ResultRemark(
                code=error.value,
                status=(
                    GeneralStatus.ALERT
                    if error in critical_error_codes
                    else GeneralStatus.WARNING
                ),
                title="Ошибка прохождения",
                description=_ERROR_DESCRIPTIONS.get(error, error.value),
            )
        )
    return result


def _summary(status: ResultStatus, score: int, completed_at: datetime) -> str:
    labels = {
        ResultStatus.PASSED: "Сценарий пройден",
        ResultStatus.PASSED_WITH_REMARKS: "Сценарий пройден с замечаниями",
        ResultStatus.FAILED: "Сценарий не пройден",
    }
    return f"{labels[status]}. Итоговая оценка: {score}/100."


_ERROR_DESCRIPTIONS = {
    ActionErrorCode.DIAGNOSTICS_NOT_RUN: "Форма учебной диагностики не была запущена.",
    ActionErrorCode.PRA_NOT_CHECKED: "Не просмотрен тренд PRA 351.",
    ActionErrorCode.FYQR_NOT_CHECKED: "Не просмотрен тренд FYQR 117.",
    ActionErrorCode.ELOU_NOT_CHECKED_AFTER_SWITCH: "После переключения не проверен блок ЭЛОУ.",
    ActionErrorCode.E15_NOT_CHECKED_AFTER_SWITCH: "После переключения не проверена Е-15.",
    ActionErrorCode.LRCA_RECOVERY_NOT_CONFIRMED: "Восстановление LRCA 605 не подтверждено.",
    ActionErrorCode.COMPLETED_BEFORE_STABLE: "Сценарий завершён до стабилизации.",
    ActionErrorCode.E15_SAFETY_LIMIT_REACHED: "LRCA 605 достиг учебной критической границы.",
    ActionErrorCode.WRONG_DIAGNOSIS_REASON: "Выбрана неверная причина неисправности.",
    ActionErrorCode.FAULT_NOT_DETECTED: "Неисправность Н-1А не выявлена.",
    ActionErrorCode.SWITCH_BEFORE_DIAGNOSIS: "Переключение начато до корректного диагноза.",
}


def _correct_diagnosis(action: RecordedAction) -> bool:
    return (
        action.target_id == "eq-n1a"
        and action.parameters.get("conclusion")
        == DiagnosisConclusion.FAULT_DETECTED.value
        and action.parameters.get("reason") == DiagnosisReason.BEARING_WEAR.value
    )


def _identifies_fault(action: RecordedAction) -> bool:
    return (
        action.target_id == "eq-n1a"
        and action.parameters.get("conclusion")
        == DiagnosisConclusion.FAULT_DETECTED.value
    )


def _has_action(
    actions: list[RecordedAction],
    action_type: ActionType,
    target_id: str,
    *,
    before: int | None = None,
    after: int | None = None,
    at_or_after: int | None = None,
) -> bool:
    return any(
        item.action_type is action_type
        and item.target_id == target_id
        and (before is None or item.virtual_time_ms <= before)
        and (after is None or item.virtual_time_ms >= after)
        and (at_or_after is None or item.virtual_time_ms >= at_or_after)
        for item in actions
    )


def _checked_component(
    actions: list[RecordedAction],
    component_id: str,
    after_ms: int,
) -> bool:
    if component_id == "eq-e15":
        return _has_action(
            actions,
            ActionType.OPEN_EQUIPMENT_CARD,
            "eq-e15",
            after=after_ms,
        )
    signal_prefixes = ("ELOU.",)
    return any(
        item.virtual_time_ms >= after_ms
        and (
            item.action_type is ActionType.OPEN_EQUIPMENT_CARD
            and item.target_id == component_id
            or item.action_type is ActionType.VIEW_SIGNAL
            and item.target_id is not None
            and item.target_id.startswith(signal_prefixes)
        )
        for item in actions
    )


def _first(items):
    return next(iter(items), None)
