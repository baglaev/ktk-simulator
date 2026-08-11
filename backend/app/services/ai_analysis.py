from __future__ import annotations

from app.domain import (
    AIAnalysisProvenance,
    AIErrorCard,
    ActionErrorCode,
    AdaptivePlanItem,
    AdaptiveRepetitionPlan,
    GeneralStatus,
    RecordedAction,
    ScenarioHintMessage,
    SessionAIAnalysis,
    SessionResult,
    TrainingMode,
)


class SessionAIAnalysisService:
    """Explain a fixed deterministic result without changing score or status."""

    def build(
        self,
        result: SessionResult,
        actions: list[RecordedAction],
        hints: list[ScenarioHintMessage],
    ) -> SessionAIAnalysis:
        detected: list[tuple[int, ActionErrorCode, RecordedAction | None]] = []
        for code in result.error_codes:
            action = next(
                (item for item in actions if code in item.error_codes),
                None,
            )
            detected.append(
                (
                    action.virtual_time_ms if action else result.elapsed_time_ms,
                    code,
                    action,
                )
            )
        detected.sort(key=lambda item: (item[0], item[1].value))

        cards: list[AIErrorCard] = []
        for order, (detected_at_ms, code, action) in enumerate(
            detected,
            start=1,
        ):
            detail = _ERROR_CARDS.get(code, _DEFAULT_CARD)
            hint_time = next(
                (
                    item.virtual_time_ms
                    for item in hints
                    if item.hint_id in detail["hint_ids"]
                ),
                None,
            )
            cards.append(
                AIErrorCard(
                    order=order,
                    code=code.value,
                    classification=detail["classification"],
                    status=(
                        GeneralStatus.ALERT
                        if code in _CRITICAL_CODES
                        else GeneralStatus.WARNING
                    ),
                    detected_at_ms=detected_at_ms,
                    user_action=(
                        action.description
                        if action is not None
                        else detail["observed"]
                    ),
                    consequence=detail["consequence"],
                    correct_approach=detail["correct"],
                    prediction=detail["prediction"],
                    hint_shown_at_ms=hint_time,
                )
            )

        strengths = [
            item.description
            for item in result.task_execution
            if item.status is GeneralStatus.SUCCESS
        ]
        recommendations = list(
            dict.fromkeys(
                _ERROR_CARDS.get(code, _DEFAULT_CARD)["correct"]
                for code in result.error_codes
            )
        )
        if not recommendations:
            recommendations.append(
                "Повторите сценарий в контрольном режиме без подсказок."
            )
        return SessionAIAnalysis(
            session_id=result.session_id,
            result_status=result.status,
            total_score=result.total_score,
            summary=(
                f"{result.summary} Разобрано ошибок: {len(cards)}. "
                "Статус и оценка рассчитаны детерминированной методикой."
            ),
            strengths=strengths,
            errors=cards,
            recommendations=recommendations,
            provenance=AIAnalysisProvenance(
                source_refs=["A-18", "учебное допущение"]
            ),
        )

    def adaptive_plan(
        self,
        result: SessionResult,
    ) -> AdaptiveRepetitionPlan:
        skills: list[tuple[str, str, str]] = []
        for code in result.error_codes:
            detail = _ERROR_CARDS.get(code, _DEFAULT_CARD)
            candidate = (
                str(detail["skill"]),
                str(detail["correct"]),
                str(detail["criterion"]),
            )
            if candidate not in skills:
                skills.append(candidate)
        if not skills:
            skills.append(
                (
                    "Закрепление полного сценария",
                    "Ошибок не обнаружено; закрепите последовательность без подсказок.",
                    "Пройти сценарий повторно без замечаний.",
                )
            )
        next_mode = (
            TrainingMode.CONTROL
            if result.status.value == "passed"
            else TrainingMode.TRAINING
        )
        return AdaptiveRepetitionPlan(
            session_id=result.session_id,
            summary=(
                "Рекомендуется контрольное повторение."
                if next_mode is TrainingMode.CONTROL
                else "Рекомендуется учебное повторение по отмеченным навыкам."
            ),
            items=[
                AdaptivePlanItem(
                    priority=index,
                    skill=skill,
                    reason=reason,
                    next_mode=next_mode,
                    success_criterion=criterion,
                )
                for index, (skill, reason, criterion) in enumerate(skills, start=1)
            ],
        )


_DEFAULT_CARD = {
    "classification": "sequence",
    "observed": "Зафиксировано отклонение от учебного алгоритма.",
    "consequence": "Снижается воспроизводимость и оценка прохождения.",
    "correct": "Разберите последовательность с инструктором и повторите этап.",
    "prediction": "При повторении без корректировки ошибка может повториться.",
    "hint_ids": set(),
    "skill": "Последовательность действий",
    "criterion": "Выполнить этап без новых ошибок последовательности.",
}


def _card(classification, observed, consequence, correct, prediction, hint_ids, skill, criterion):
    return {
        "classification": classification,
        "observed": observed,
        "consequence": consequence,
        "correct": correct,
        "prediction": prediction,
        "hint_ids": set(hint_ids),
        "skill": skill,
        "criterion": criterion,
    }


_ERROR_CARDS = {
    ActionErrorCode.DIAGNOSTICS_NOT_RUN: _card("diagnostics", "Диагностика Н-1А не была запущена.", "Диагноз зафиксирован без предусмотренного этапа формы.", "Запустите диагностику Н-1А перед отправкой заключения.", "Этап сбора признаков может быть пропущен снова.", ["run-diagnostics"], "Работа с диагностикой", "Запустить run_diagnostics до submit_diagnosis."),
    ActionErrorCode.PRA_NOT_CHECKED: _card("monitoring", "PRA 351 не просмотрен.", "Не подтверждено влияние Н-1А на линию.", "До диагноза сопоставьте тренд Н-1А с PRA 351.", "Диагноз может быть сделан без проверки связанного параметра.", ["compare-line-signals"], "Анализ связанных трендов", "Просмотреть PRA 351 до диагноза."),
    ActionErrorCode.FYQR_NOT_CHECKED: _card("monitoring", "FYQR 117 не просмотрен.", "Не подтверждено изменение расхода.", "До диагноза сопоставьте тренд Н-1А с FYQR 117.", "Можно пропустить развитие снижения расхода.", ["compare-line-signals"], "Анализ связанных трендов", "Просмотреть FYQR 117 до диагноза."),
    ActionErrorCode.WRONG_DIAGNOSIS_REASON: _card("diagnostics", "Выбран неверный вариант диагностики.", "Зафиксирован ошибочный учебный вывод.", "Сопоставьте все признаки COMPAX и связанные технологические тренды.", "Без корректировки диагностическая ошибка может повториться.", ["submit-diagnosis"], "Диагностика Н-1А", "Выбрать верный вариант после проверки признаков."),
    ActionErrorCode.FAULT_NOT_DETECTED: _card("diagnostics", "Неисправность не подтверждена.", "Развивающийся отказ продолжает влиять на модель.", "Зафиксируйте неисправность только после анализа доступных признаков.", "Без диагноза переключение будет несвоевременным.", ["inspect-n1a"], "Распознавание отказа", "Зафиксировать корректный диагноз до переключения."),
    ActionErrorCode.SWITCH_BEFORE_DIAGNOSIS: _card("sequence", "Переключение начато до диагноза.", "Нарушена проверяемая учебная последовательность.", "Сначала подтвердите диагноз, затем меняйте конфигурацию насосов.", "Ошибка последовательности снизит итоговую оценку.", ["review-pump-configuration"], "Последовательность переключения", "Зафиксировать диагноз раньше первого переключения."),
    ActionErrorCode.N1A_STOPPED_BEFORE_N1B: _card("safety", "Н-1А остановлен до запуска Н-1Б.", "Учебная модель фиксирует потерю резервирования.", "Сначала запустите Н-1Б, затем остановите Н-1А.", "Возможна небезопасная конфигурация насосной группы.", ["unsafe-pump-configuration"], "Безопасное резервирование", "Запустить Н-1Б раньше остановки Н-1А."),
    ActionErrorCode.N1A_RESTARTED_AFTER_SWITCH: _card("sequence", "Н-1А повторно запущен после остановки.", "Нарушена достигнутая конфигурация переключения.", "После запуска Н-1Б остановите Н-1А и не запускайте его повторно.", "Повторный запуск неисправного насоса может вернуть небезопасное состояние.", ["review-pump-configuration"], "Последовательность переключения", "Не запускать Н-1А повторно после его остановки."),
    ActionErrorCode.MULTIPLE_PUMPS_STOPPED: _card("safety", "Н-1А остановлен при ещё не запущенном Н-1Б.", "Одновременно остановлены неисправный и резервный насосы.", "Сначала запустите Н-1Б, затем остановите Н-1А.", "При повторении возможна временная потеря резервирования.", ["unsafe-pump-configuration"], "Безопасное резервирование", "Не допускать одновременной остановки Н-1А и Н-1Б."),
    ActionErrorCode.ELOU_NOT_CHECKED_AFTER_SWITCH: _card("monitoring", "ЭЛОУ не проверен после переключения.", "Не подтверждено ограничение последствий.", "После переключения проверьте состояние блока ЭЛОУ.", "Можно пропустить продолжающееся снижение downstream-параметров.", ["monitor-recovery"], "Контроль последствий", "Проверить ЭЛОУ после переключения."),
    ActionErrorCode.E15_NOT_CHECKED_AFTER_SWITCH: _card("monitoring", "Е-15 не проверена после переключения.", "Не подтвержден контроль выходной ёмкости.", "После переключения проверьте Е-15 и LRCA 605.", "Критическое снижение LRCA 605 может остаться незамеченным.", ["monitor-recovery"], "Контроль последствий", "Проверить Е-15 после переключения."),
    ActionErrorCode.LRCA_RECOVERY_NOT_CONFIRMED: _card("monitoring", "LRCA 605 не проверен после переключения.", "Восстановление уровня не подтверждено пользователем.", "Просмотрите LRCA 605 после смены насосной конфигурации.", "Сценарий может быть завершён без проверки восстановления.", ["monitor-recovery"], "Подтверждение восстановления", "Просмотреть LRCA 605 после переключения."),
    ActionErrorCode.COMPLETED_BEFORE_STABLE: _card("safety", "Сценарий завершён до стабилизации.", "Учебная модель не подтвердила восстановление.", "Дождитесь автоматического завершения после стабилизации.", "Преждевременное завершение останется критической ошибкой.", ["monitor-recovery"], "Контроль стабилизации", "Дождаться состояния objectives_completed."),
    ActionErrorCode.E15_SAFETY_LIMIT_REACHED: _card("safety", "LRCA 605 достиг 20%.", "Достигнута учебная критическая граница.", "Диагностируйте и начните корректное переключение раньше.", "При той же задержке сценарий снова завершится неуспешно.", ["inspect-n1a"], "Своевременность реакции", "Завершить переключение до достижения границы."),
}

_CRITICAL_CODES = {
    ActionErrorCode.E15_SAFETY_LIMIT_REACHED,
    ActionErrorCode.COMPLETED_BEFORE_STABLE,
    ActionErrorCode.MULTIPLE_PUMPS_STOPPED,
}
