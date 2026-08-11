from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from app.domain import (
    ActionType,
    GeneralStatus,
    HintEvidence,
    HintProvenance,
    ModelSnapshot,
    RecordedAction,
    ScenarioHintMessage,
    TrainingMode,
)


class ScenarioHintService:
    """Cheap prepared hints; no LLM and no network call in the live loop."""

    def __init__(self) -> None:
        self._emitted: dict[UUID, set[str]] = {}

    def reset(self, session_id: UUID) -> None:
        self._emitted.pop(session_id, None)

    def evaluate(
        self,
        snapshot: ModelSnapshot,
        actions: list[RecordedAction],
    ) -> ScenarioHintMessage | None:
        if snapshot.mode is TrainingMode.CONTROL:
            return None

        emitted = self._emitted.setdefault(snapshot.session_id, set())
        for hint_id, evaluator in self._rules():
            if hint_id in emitted:
                continue
            message = evaluator(snapshot, actions)
            if message is None:
                continue
            emitted.add(hint_id)
            return message
        return None

    def _rules(self) -> tuple[
        tuple[str, Callable[[ModelSnapshot, list[RecordedAction]], ScenarioHintMessage | None]],
        ...,
    ]:
        return (
            ("unsafe-pump-configuration", self._unsafe_configuration),
            ("scenario-completed", self._completed),
            ("monitor-recovery", self._monitor_recovery),
            ("review-pump-configuration", self._review_switch),
            ("submit-diagnosis", self._submit_diagnosis),
            ("run-diagnostics", self._run_diagnostics),
            ("compare-line-signals", self._compare_signals),
            ("inspect-n1a", self._inspect_n1a),
        )

    def _unsafe_configuration(self, snapshot, actions):
        states = {item.component_id: item.operating_state.value for item in snapshot.components}
        if states.get("eq-n1a") == "stopped" and states.get("eq-n1b") == "stopped":
            return self._hint(
                snapshot,
                "unsafe-pump-configuration",
                GeneralStatus.ALERT,
                "Проверьте резервирование",
                "Учебная конфигурация насосной группы не обеспечивает подачу.",
                [HintEvidence(kind="component", ref_id="eq-n1-discharge", fact="Н-1А и Н-1Б остановлены")],
            )
        return None

    def _completed(self, snapshot, actions):
        if snapshot.scenario_state.status.value != "completed":
            return None
        return self._hint(
            snapshot,
            "scenario-completed",
            GeneralStatus.SUCCESS if snapshot.scenario_state.completion_reason and snapshot.scenario_state.completion_reason.value == "objectives_completed" else GeneralStatus.ALERT,
            "Сценарий завершён",
            "Откройте итоговый результат и разбор прохождения.",
            [HintEvidence(kind="action", ref_id="result", fact="Модель перешла в конечное состояние")],
        )

    def _monitor_recovery(self, snapshot, actions):
        discharge = self._component(snapshot, "eq-n1-discharge")
        if discharge is None or not discharge.state.get("recoveryActive"):
            return None
        return self._hint(
            snapshot,
            "monitor-recovery",
            GeneralStatus.WARNING,
            "Контролируйте восстановление",
            "Сопоставьте PRA 351, FYQR 117, ЭЛОУ, Е-15 и дождитесь стабилизации учебной модели.",
            [HintEvidence(kind="component", ref_id="eq-n1-discharge", fact="Идёт учебное восстановление")],
        )

    def _review_switch(self, snapshot, actions):
        if not self._correct_diagnosis(actions):
            return None
        discharge = self._component(snapshot, "eq-n1-discharge")
        if discharge is not None and discharge.state.get("safePumpConfiguration"):
            return None
        return self._hint(
            snapshot,
            "review-pump-configuration",
            GeneralStatus.WARNING,
            "Проверьте насосную конфигурацию",
            "Диагноз зарегистрирован, но безопасная учебная конфигурация ещё не подтверждена.",
            [HintEvidence(kind="action", ref_id="submit_diagnosis", fact="Верный учебный диагноз зарегистрирован")],
        )

    def _submit_diagnosis(self, snapshot, actions):
        if not self._has(actions, ActionType.RUN_DIAGNOSTICS) or self._has(actions, ActionType.SUBMIT_DIAGNOSIS):
            return None
        return self._hint(
            snapshot,
            "submit-diagnosis",
            GeneralStatus.WARNING,
            "Зафиксируйте вывод",
            "Диагностические данные собраны. Отправьте заключение формы диагностики.",
            [HintEvidence(kind="action", ref_id="run_diagnostics", fact="Диагностика запущена")],
        )

    def _run_diagnostics(self, snapshot, actions):
        if not self._has(actions, ActionType.VIEW_SIGNAL, "PRA351") or not self._has(actions, ActionType.VIEW_SIGNAL, "FYQR117"):
            return None
        if self._has(actions, ActionType.RUN_DIAGNOSTICS) or self._has(actions, ActionType.SUBMIT_DIAGNOSIS):
            return None
        return self._hint(
            snapshot,
            "run-diagnostics",
            GeneralStatus.WARNING,
            "Сопоставьте признаки",
            "Линейные сигналы просмотрены. Запустите учебную диагностику Н-1А.",
            [HintEvidence(kind="action", ref_id="view_signal", fact="PRA 351 и FYQR 117 просмотрены")],
        )

    def _compare_signals(self, snapshot, actions):
        n1a = self._component(snapshot, "eq-n1a")
        if n1a is None or n1a.status.value not in {"warning", "alert"}:
            return None
        if not self._has(actions, ActionType.OPEN_EQUIPMENT_CARD, "eq-n1a"):
            return None
        if self._has(actions, ActionType.VIEW_SIGNAL, "PRA351") and self._has(actions, ActionType.VIEW_SIGNAL, "FYQR117"):
            return None
        return self._hint(
            snapshot,
            "compare-line-signals",
            GeneralStatus.WARNING,
            "Сравните связанные сигналы",
            "Сопоставьте изменения Н-1А с трендами PRA 351 и FYQR 117.",
            [HintEvidence(kind="signal", ref_id="PRA351", fact="Нужна проверка связанных трендов")],
        )

    def _inspect_n1a(self, snapshot, actions):
        n1a = self._component(snapshot, "eq-n1a")
        if n1a is None or n1a.status.value not in {"warning", "alert"}:
            return None
        if self._has(actions, ActionType.OPEN_EQUIPMENT_CARD, "eq-n1a"):
            return None
        return self._hint(
            snapshot,
            "inspect-n1a",
            GeneralStatus.WARNING,
            "Проверьте Н-1А",
            "Статус Н-1А изменился. Откройте карточку и изучите диагностические признаки.",
            [HintEvidence(kind="component", ref_id="eq-n1a", fact=f"Статус: {n1a.status.value}")],
        )

    @staticmethod
    def _component(snapshot: ModelSnapshot, component_id: str):
        return next((item for item in snapshot.components if item.component_id == component_id), None)

    @staticmethod
    def _has(actions: list[RecordedAction], action_type: ActionType, target_id: str | None = None) -> bool:
        return any(item.action_type is action_type and (target_id is None or item.target_id == target_id) for item in actions)

    @staticmethod
    def _correct_diagnosis(actions: list[RecordedAction]) -> bool:
        return any(
            item.action_type is ActionType.SUBMIT_DIAGNOSIS
            and item.target_id == "eq-n1a"
            and (
                item.parameters.get("diagnosis") == "1"
                or (
                    item.parameters.get("conclusion") == "fault_detected"
                    and item.parameters.get("reason") == "bearing_wear"
                )
            )
            for item in actions
        )

    @staticmethod
    def _hint(snapshot, hint_id, level, title, message, evidence):
        return ScenarioHintMessage(
            session_id=snapshot.session_id,
            virtual_time_ms=snapshot.timing.elapsed_ms,
            hint_id=hint_id,
            level=level,
            title=title,
            message=message,
            evidence=evidence,
            provenance=HintProvenance(source_refs=["A-18", "учебное допущение"]),
        )
