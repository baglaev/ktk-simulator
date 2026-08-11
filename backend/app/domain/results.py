from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import APIModel
from app.domain.enums import (
    ActionErrorCode,
    CompletionReason,
    GeneralStatus,
    ResultStatus,
    ScenarioOutcome,
    SessionStatus,
    TrainingMode,
)


ACTION_ERROR_DESCRIPTIONS = {
    ActionErrorCode.SWITCH_BEFORE_DIAGNOSIS: "Переключение начато до корректного диагноза.",
    ActionErrorCode.HEALTHY_PUMP_SELECTED: "В качестве неисправного выбран исправный насос.",
    ActionErrorCode.FAULT_NOT_DETECTED: "Неисправность Н-1А не выявлена.",
    ActionErrorCode.WRONG_DIAGNOSIS_REASON: "Выбран неверный вариант диагностики.",
    ActionErrorCode.DIAGNOSIS_TOO_LATE: "Диагноз зафиксирован слишком поздно.",
    ActionErrorCode.DIAGNOSIS_WITHOUT_PRA_CHECK: "Диагноз поставлен без предварительной проверки PRA 351.",
    ActionErrorCode.DIAGNOSIS_WITHOUT_FYQR_CHECK: "Диагноз поставлен без предварительной проверки FYQR 117.",
    ActionErrorCode.WRONG_DIAGNOSIS_CORRECTED: "Первоначально неверный диагноз был исправлен.",
    ActionErrorCode.DIAGNOSTICS_NOT_RUN: "Форма учебной диагностики не была запущена.",
    ActionErrorCode.PUMP_COMMAND_BEFORE_WARNING: "Команда насосу отправлена до появления предупреждения.",
    ActionErrorCode.N1A_STOPPED_BEFORE_N1B: "Н-1А остановлен до запуска резервного Н-1Б.",
    ActionErrorCode.N1A_STOPPED_WITHOUT_DIAGNOSIS: "Н-1А остановлен без подтверждённого диагноза.",
    ActionErrorCode.HEALTHY_PUMP_STOPPED: "Остановлен исправный насос.",
    ActionErrorCode.N1A_LEFT_RUNNING: "После запуска Н-1Б неисправный Н-1А оставлен в работе.",
    ActionErrorCode.N1B_STOPPED_AFTER_START: "Резервный Н-1Б повторно остановлен после запуска.",
    ActionErrorCode.N1A_RESTARTED_AFTER_SWITCH: "Н-1А повторно запущен после его остановки.",
    ActionErrorCode.MULTIPLE_PUMPS_STOPPED: "Н-1А остановлен, пока резервный Н-1Б ещё не был запущен.",
    ActionErrorCode.UNNECESSARY_REPEATED_SWITCHING: "Повторно отправлена команда, уже соответствующая состоянию насоса.",
    ActionErrorCode.WARNING_IGNORED: "Предупреждение о неисправности оставлено без подтверждённого диагноза.",
    ActionErrorCode.PRA_NOT_CHECKED: "Не просмотрен тренд PRA 351.",
    ActionErrorCode.FYQR_NOT_CHECKED: "Не просмотрен тренд FYQR 117.",
    ActionErrorCode.ELOU_NOT_CHECKED_AFTER_SWITCH: "После переключения не проверен блок ЭЛОУ.",
    ActionErrorCode.E15_NOT_CHECKED_AFTER_SWITCH: "После переключения не проверена Е-15.",
    ActionErrorCode.LRCA_RECOVERY_NOT_CONFIRMED: "Восстановление LRCA 605 не подтверждено.",
    ActionErrorCode.COMPLETED_BEFORE_STABLE: "Сценарий завершён до стабилизации.",
    ActionErrorCode.E15_SAFETY_LIMIT_REACHED: "LRCA 605 достиг учебной критической границы.",
}


class ScoreSection(APIModel):
    score: int = Field(ge=0)
    max_score: int = Field(gt=0)


class TaskExecutionItem(APIModel):
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: GeneralStatus
    completed_at_ms: int | None = Field(default=None, ge=0)
    description: str = Field(min_length=1)


class ResultParameter(APIModel):
    parameter_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    final_value: int
    minimum_value: int
    unit: str = Field(min_length=1)
    status: GeneralStatus


class ResultRemark(APIModel):
    code: str = Field(min_length=1)
    status: GeneralStatus
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SessionResult(APIModel):
    """Deterministic SCR-04 result. AI assessment can be added separately."""

    session_id: UUID
    rubric_version: str = "SCR04-A18-2.0"
    status: ResultStatus
    outcome: ScenarioOutcome
    mode: TrainingMode
    completion_reason: CompletionReason
    summary: str = Field(min_length=1)
    elapsed_time_ms: int = Field(ge=0)
    total_score: int = Field(ge=0, le=100)
    max_score: int = 100
    diagnosis: ScoreSection
    stabilization: ScoreSection
    consequence_control: ScoreSection
    timeliness: ScoreSection
    penalties: int = Field(le=0)
    error_codes: list[ActionErrorCode] = Field(default_factory=list)
    critical_failure_reasons: list[str] = Field(default_factory=list)
    task_execution: list[TaskExecutionItem] = Field(default_factory=list)
    controlled_parameters: list[ResultParameter] = Field(default_factory=list)
    remarks: list[ResultRemark] = Field(default_factory=list)
    completed_at: AwareDatetime

    @model_validator(mode="before")
    @classmethod
    def adopt_legacy_scr04_payload(cls, value):
        """Read 0.3.x result JSON retained in an upgraded local database."""

        if not isinstance(value, dict):
            return value
        payload = dict(value)
        parameters_key = (
            "controlledParameters"
            if "controlledParameters" in payload
            else "controlled_parameters"
        )
        parameters = payload.get(parameters_key)
        if isinstance(parameters, list):
            payload[parameters_key] = [
                _adopt_legacy_parameter(parameter)
                for parameter in parameters
            ]

        remarks = payload.get("remarks")
        if isinstance(remarks, list):
            payload["remarks"] = [
                _adopt_result_remark(remark) for remark in remarks
            ]

        if "status" in payload or "resultStatus" in payload:
            return payload
        outcome = payload.get("outcome", "failed")
        payload.update(
            {
                "status": "passed" if outcome == "success" else "failed",
                "mode": "training",
                "completionReason": (
                    "objectives_completed"
                    if outcome == "success"
                    else "completed_before_stabilization"
                ),
                "summary": "Архивный результат сессии версии 0.3.x.",
                "elapsedTimeMs": 0,
            }
        )
        return payload


def _adopt_result_remark(value):
    """Replace archived technical error codes with current user-facing text."""

    if not isinstance(value, dict):
        return value
    remark = dict(value)
    try:
        error_code = ActionErrorCode(remark.get("code"))
    except (TypeError, ValueError):
        return remark
    if remark.get("status") == GeneralStatus.WARNING.value:
        remark["title"] = "Замечание"
    remark["description"] = ACTION_ERROR_DESCRIPTIONS[error_code]
    return remark


def _adopt_legacy_parameter(value):
    """Round fractional values written before the integer API contract."""

    if not isinstance(value, dict):
        return value
    parameter = dict(value)
    for camel_key, snake_key in (
        ("finalValue", "final_value"),
        ("minimumValue", "minimum_value"),
    ):
        key = camel_key if camel_key in parameter else snake_key
        number = parameter.get(key)
        if isinstance(number, float):
            parameter[key] = int(
                Decimal(str(number)).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP,
                )
            )
    return parameter


class TraineeResultSummary(APIModel):
    """Compact completed-attempt row for the instructor dashboard."""

    session_id: UUID
    trainee_id: str = Field(min_length=1)
    instructor_id: str | None = None
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    mode: TrainingMode
    session_status: SessionStatus
    result_status: ResultStatus
    outcome: ScenarioOutcome
    total_score: int = Field(ge=0, le=100)
    max_score: int = Field(gt=0)
    elapsed_time_ms: int = Field(ge=0)
    completed_at: AwareDatetime


class TraineeResultsPage(APIModel):
    """Paginated completed results returned to the instructor frontend."""

    items: list[TraineeResultSummary] = Field(default_factory=list)
    total: int = Field(ge=0)
    limit: int = Field(gt=0)
    offset: int = Field(ge=0)


class TraineeResultsCollection(APIModel):
    """All completed results returned without frontend query parameters."""

    items: list[TraineeResultSummary] = Field(default_factory=list)
    total: int = Field(ge=0)
