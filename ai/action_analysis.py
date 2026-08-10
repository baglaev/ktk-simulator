"""Deterministic analysis of the MVP trainee action sequence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


Action = Mapping[str, Any]
Predicate = Callable[[Action], bool]


class ActionSequenceAnalyzer:
    """Calculate training stages and timing without asking an LLM to judge facts."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        path = (
            Path(rules_path)
            if rules_path
            else Path(__file__).parent / "data" / "action_analysis_rules.json"
        )
        with path.open(encoding="utf-8") as source:
            rules = json.load(source)
        windows = rules["trainingWindows"]
        self._warning_at_ms = int(windows["warningAtMs"])
        self._diagnosis_before_ms = int(windows["diagnosisBeforeOrAtMs"])
        self._preferred_switch_before_ms = int(
            windows["preferredSwitchBeforeOrAtMs"]
        )
        self._late_switch_before_ms = int(windows["lateSwitchBeforeOrAtMs"])
        self._source_refs = tuple(rules["provenance"]["sourceRefs"])

    def analyze(
        self,
        actions: Sequence[Action],
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized = [dict(item) for item in actions if isinstance(item, Mapping)]
        first_diagnosis = self._first(
            normalized, lambda item: self._type(item) == "submit_diagnosis"
        )
        diagnosis_cutoff = (
            self._time(first_diagnosis[1]) if first_diagnosis is not None else None
        )

        open_n1a = self._first(
            normalized,
            lambda item: self._type(item) == "open_equipment_card"
            and self._target(item) == "eq-n1a"
            and self._time(item) is not None
            and self._time(item) >= self._warning_at_ms,
        )
        pra_before_diagnosis = self._first_signal_before(
            normalized, "PRA351", diagnosis_cutoff
        )
        fyqr_before_diagnosis = self._first_signal_before(
            normalized, "FYQR117", diagnosis_cutoff
        )

        diagnoses = [
            (index, item)
            for index, item in enumerate(normalized)
            if self._type(item) == "submit_diagnosis"
        ]
        correct_diagnosis = next(
            (
                (index, item)
                for index, item in diagnoses
                if self._is_correct_diagnosis(item)
            ),
            None,
        )
        start_n1b = self._first(
            normalized,
            lambda item: self._type(item) == "start_pump"
            and self._target(item) == "eq-n1b",
        )
        stop_n1a = self._first(
            normalized,
            lambda item: self._type(item) == "stop_pump"
            and self._target(item) == "eq-n1a",
        )

        switch_completed_at = self._latest_time(start_n1b, stop_n1a)
        reserve_before_stop = self._is_before(start_n1b, stop_n1a)
        diagnosis_before_switch = self._is_before(correct_diagnosis, start_n1b)
        if diagnosis_before_switch and stop_n1a is not None:
            diagnosis_before_switch = self._is_before(correct_diagnosis, stop_n1a)

        recovery_checks = self._recovery_checks(normalized, switch_completed_at)
        stages = [
            self._detection_stage(open_n1a, pra_before_diagnosis, fyqr_before_diagnosis),
            self._diagnosis_stage(diagnoses, correct_diagnosis),
            self._switch_stage(
                start_n1b,
                stop_n1a,
                reserve_before_stop,
                diagnosis_before_switch,
            ),
            self._recovery_stage(switch_completed_at, recovery_checks),
            self._completion_stage(result),
        ]

        first_reaction = self._first(
            normalized,
            lambda item: self._time(item) is not None
            and self._time(item) >= self._warning_at_ms
            and self._type(item)
            in {
                "open_equipment_card",
                "view_signal",
                "run_diagnostics",
                "submit_diagnosis",
                "start_pump",
                "stop_pump",
            },
        )
        first_reaction_at = self._pair_time(first_reaction)
        correct_diagnosis_at = self._pair_time(correct_diagnosis)
        recovery_times = [
            self._pair_time(item) for item in recovery_checks.values() if item is not None
        ]
        recovery_last_check_at = max(recovery_times) if recovery_times else None

        strengths = self._strengths(
            stages,
            correct_diagnosis_at=correct_diagnosis_at,
            switch_completed_at=switch_completed_at,
        )
        focus_areas = self._focus_areas(
            open_n1a=open_n1a,
            pra=pra_before_diagnosis,
            fyqr=fyqr_before_diagnosis,
            diagnoses=diagnoses,
            correct_diagnosis=correct_diagnosis,
            start_n1b=start_n1b,
            stop_n1a=stop_n1a,
            reserve_before_stop=reserve_before_stop,
            diagnosis_before_switch=diagnosis_before_switch,
            recovery_checks=recovery_checks,
            outcome=str(result.get("outcome", result.get("status", "unknown"))),
        )

        return {
            "scenarioId": "MVP-SC-01",
            "stages": stages,
            "timing": {
                "warningAtMs": self._warning_at_ms,
                "firstReactionAtMs": first_reaction_at,
                "firstReactionDelayMs": (
                    first_reaction_at - self._warning_at_ms
                    if first_reaction_at is not None
                    else None
                ),
                "correctDiagnosisAtMs": correct_diagnosis_at,
                "switchCompletedAtMs": switch_completed_at,
                "recoveryLastCheckAtMs": recovery_last_check_at,
            },
            "sequence": {
                "diagnosisBeforePumpActions": diagnosis_before_switch,
                "reserveStartedBeforeFaultyPumpStopped": reserve_before_stop,
                "diagnosisWithinEducationalWindow": (
                    correct_diagnosis_at <= self._diagnosis_before_ms
                    if correct_diagnosis_at is not None
                    else None
                ),
                "switchWithinPreferredEducationalWindow": (
                    switch_completed_at <= self._preferred_switch_before_ms
                    if switch_completed_at is not None
                    else None
                ),
                "switchBeforeLateEducationalBoundary": (
                    switch_completed_at <= self._late_switch_before_ms
                    if switch_completed_at is not None
                    else None
                ),
            },
            "timeline": [
                self._timeline_item(index, action)
                for index, action in enumerate(normalized[:200], start=1)
            ],
            "strengths": strengths,
            "focusAreas": focus_areas,
            "provenance": {
                "method": "deterministic_action_analysis",
                "sourceRefs": list(self._source_refs),
            },
        }

    def _detection_stage(
        self,
        card: tuple[int, Action] | None,
        pra: tuple[int, Action] | None,
        fyqr: tuple[int, Action] | None,
    ) -> dict[str, Any]:
        completed = [item for item in (card, pra, fyqr) if item is not None]
        status = "success" if len(completed) == 3 else "warning" if completed else "alert"
        observations = [
            self._presence(card, "Карточка Н-1А открыта", "Карточка Н-1А не открыта"),
            self._presence(pra, "PRA 351 просмотрен до диагноза", "PRA 351 не просмотрен до диагноза"),
            self._presence(fyqr, "FYQR 117 просмотрен до диагноза", "FYQR 117 не просмотрен до диагноза"),
        ]
        return self._stage(
            "detection",
            "Обнаружение и сбор признаков",
            status,
            self._max_pair_time(completed),
            observations,
            ["A-02", "A-18", "учебное допущение"],
        )

    def _diagnosis_stage(
        self,
        diagnoses: list[tuple[int, Action]],
        correct: tuple[int, Action] | None,
    ) -> dict[str, Any]:
        if correct is not None:
            status = "success"
            observations = ["Корректный учебный диагноз зафиксирован"]
            completed_at = self._pair_time(correct)
        elif diagnoses:
            status = "warning"
            observations = ["Учебный диагноз отправлен, но не подтвержден как корректный"]
            completed_at = self._pair_time(diagnoses[0])
        else:
            status = "alert"
            observations = ["Учебный диагноз не зарегистрирован"]
            completed_at = None
        return self._stage(
            "diagnosis",
            "Диагностика",
            status,
            completed_at,
            observations,
            ["A-02", "A-18", "учебное допущение"],
        )

    def _switch_stage(
        self,
        start_n1b: tuple[int, Action] | None,
        stop_n1a: tuple[int, Action] | None,
        reserve_before_stop: bool | None,
        diagnosis_before_switch: bool | None,
    ) -> dict[str, Any]:
        both = start_n1b is not None and stop_n1a is not None
        success = both and reserve_before_stop is True and diagnosis_before_switch is True
        status = "success" if success else "warning" if start_n1b or stop_n1a else "alert"
        observations = [
            self._presence(start_n1b, "Н-1Б запущен в учебной модели", "Запуск Н-1Б не зарегистрирован"),
            self._presence(stop_n1a, "Н-1А остановлен в учебной модели", "Остановка Н-1А не зарегистрирована"),
        ]
        if both:
            observations.append(
                "Н-1Б запущен раньше остановки Н-1А"
                if reserve_before_stop
                else "Н-1А остановлен раньше запуска Н-1Б"
            )
        if start_n1b or stop_n1a:
            observations.append(
                "Диагноз зафиксирован до переключения"
                if diagnosis_before_switch
                else "Переключение начато до корректного диагноза"
            )
        return self._stage(
            "switching",
            "Учебное переключение насосов",
            status,
            self._latest_time(start_n1b, stop_n1a),
            observations,
            ["A-17", "A-18", "учебное допущение"],
        )

    def _recovery_stage(
        self,
        switch_at: int | None,
        checks: Mapping[str, tuple[int, Action] | None],
    ) -> dict[str, Any]:
        present = [item for item in checks.values() if item is not None]
        if switch_at is None:
            status = "alert"
        elif len(present) == len(checks):
            status = "success"
        elif present:
            status = "warning"
        else:
            status = "alert"
        labels = {
            "PRA351": "PRA 351",
            "FYQR117": "FYQR 117",
            "eq-elou": "блок ЭЛОУ",
            "eq-e15": "Е-15",
            "LRCA605": "LRCA 605",
        }
        observations = [
            self._presence(
                checks[key],
                f"После переключения проверен {label}",
                f"После переключения не проверен {label}",
            )
            for key, label in labels.items()
        ]
        return self._stage(
            "recovery_control",
            "Контроль восстановления",
            status,
            self._max_pair_time(present),
            observations,
            ["A-17", "A-18", "учебное допущение"],
        )

    @staticmethod
    def _completion_stage(result: Mapping[str, Any]) -> dict[str, Any]:
        outcome = str(result.get("outcome", result.get("status", "unknown")))
        status = (
            "success"
            if outcome in {"success", "completed", "passed"}
            else "alert"
            if outcome in {"failed", "failure"}
            else "warning"
        )
        critical = result.get(
            "criticalFailureReasons", result.get("critical_failure_reasons", [])
        )
        observations = [f"Итог учебного сценария: {outcome}"]
        if isinstance(critical, Sequence) and not isinstance(critical, (str, bytes)):
            observations.extend(str(item) for item in critical)
        return ActionSequenceAnalyzer._stage(
            "completion",
            "Завершение",
            status,
            None,
            observations,
            ["A-18", "учебное допущение"],
        )

    def _recovery_checks(
        self,
        actions: list[Action],
        switch_at: int | None,
    ) -> dict[str, tuple[int, Action] | None]:
        def after_switch(item: Action) -> bool:
            time_ms = self._time(item)
            return switch_at is not None and time_ms is not None and time_ms > switch_at

        return {
            "PRA351": self._first(
                actions,
                lambda item: after_switch(item)
                and self._type(item) == "view_signal"
                and self._target(item) == "PRA351",
            ),
            "FYQR117": self._first(
                actions,
                lambda item: after_switch(item)
                and self._type(item) == "view_signal"
                and self._target(item) == "FYQR117",
            ),
            "eq-elou": self._first(
                actions,
                lambda item: after_switch(item)
                and self._type(item) == "open_equipment_card"
                and self._target(item) == "eq-elou",
            ),
            "eq-e15": self._first(
                actions,
                lambda item: after_switch(item)
                and self._type(item) == "open_equipment_card"
                and self._target(item) == "eq-e15",
            ),
            "LRCA605": self._first(
                actions,
                lambda item: after_switch(item)
                and self._type(item) == "view_signal"
                and self._target(item) == "LRCA605",
            ),
        }

    def _strengths(
        self,
        stages: list[dict[str, Any]],
        *,
        correct_diagnosis_at: int | None,
        switch_completed_at: int | None,
    ) -> list[str]:
        statuses = {item["stageId"]: item["status"] for item in stages}
        strengths: list[str] = []
        if statuses["detection"] == "success":
            strengths.append("Перед диагнозом собраны основные учебные признаки Н-1А.")
        if statuses["diagnosis"] == "success":
            message = "Учебная неисправность Н-1А определена корректно."
            if correct_diagnosis_at is not None and correct_diagnosis_at <= self._diagnosis_before_ms:
                message = "Учебная неисправность Н-1А определена в заданном сценарном окне."
            strengths.append(message)
        if statuses["switching"] == "success":
            message = "Соблюдена учебная последовательность переключения насосов."
            if switch_completed_at is not None and switch_completed_at <= self._preferred_switch_before_ms:
                message = "Учебное переключение выполнено в правильной последовательности и сценарном окне."
            strengths.append(message)
        if statuses["recovery_control"] == "success":
            strengths.append("После переключения проверены все связанные компоненты и сигналы MVP.")
        return strengths

    @staticmethod
    def _focus_areas(
        *,
        open_n1a: tuple[int, Action] | None,
        pra: tuple[int, Action] | None,
        fyqr: tuple[int, Action] | None,
        diagnoses: list[tuple[int, Action]],
        correct_diagnosis: tuple[int, Action] | None,
        start_n1b: tuple[int, Action] | None,
        stop_n1a: tuple[int, Action] | None,
        reserve_before_stop: bool | None,
        diagnosis_before_switch: bool | None,
        recovery_checks: Mapping[str, tuple[int, Action] | None],
        outcome: str,
    ) -> list[str]:
        focus: list[str] = []
        missing_detection = [
            label
            for item, label in (
                (open_n1a, "карточку Н-1А"),
                (pra, "PRA 351"),
                (fyqr, "FYQR 117"),
            )
            if item is None
        ]
        if missing_detection:
            focus.append(
                "До диагноза отработайте проверку: " + ", ".join(missing_detection) + "."
            )
        if not diagnoses:
            focus.append("Зафиксируйте учебный диагноз до изменения конфигурации насосов.")
        elif correct_diagnosis is None:
            focus.append("Повторите сопоставление признаков для корректного учебного диагноза.")
        if start_n1b is None or stop_n1a is None:
            focus.append("Завершите оба шага учебного переключения насосной группы.")
        elif not reserve_before_stop:
            focus.append("Повторите учебную последовательность с подтверждением резерва до остановки Н-1А.")
        if (start_n1b or stop_n1a) and not diagnosis_before_switch:
            focus.append("Не начинайте учебное переключение до фиксации корректного диагноза.")
        missing_recovery = [
            label
            for key, label in (
                ("PRA351", "PRA 351"),
                ("FYQR117", "FYQR 117"),
                ("eq-elou", "блок ЭЛОУ"),
                ("eq-e15", "Е-15"),
                ("LRCA605", "LRCA 605"),
            )
            if recovery_checks[key] is None
        ]
        if start_n1b is not None and stop_n1a is not None and missing_recovery:
            focus.append(
                "После переключения проверьте: " + ", ".join(missing_recovery) + "."
            )
        if outcome in {"failed", "failure"}:
            focus.append("Перед завершением подтвердите стабилизацию учебной модели.")
        return list(dict.fromkeys(focus))

    def _first_signal_before(
        self,
        actions: list[Action],
        target_id: str,
        cutoff: int | None,
    ) -> tuple[int, Action] | None:
        return self._first(
            actions,
            lambda item: self._type(item) == "view_signal"
            and self._target(item) == target_id
            and (cutoff is None or (self._time(item) is not None and self._time(item) < cutoff)),
        )

    @staticmethod
    def _first(
        actions: list[Action], predicate: Predicate
    ) -> tuple[int, Action] | None:
        return next(
            ((index, item) for index, item in enumerate(actions) if predicate(item)),
            None,
        )

    @staticmethod
    def _type(action: Action) -> str:
        raw = action.get("actionType", action.get("action_type", ""))
        return str(raw) if raw is not None else ""

    @staticmethod
    def _target(action: Action) -> str:
        raw = action.get("targetId", action.get("target_id", ""))
        return str(raw) if raw is not None else ""

    @staticmethod
    def _time(action: Action) -> int | None:
        raw = action.get(
            "virtualTimeMs",
            action.get("virtual_time_ms", action.get("elapsedTimeMs", action.get("elapsedMs"))),
        )
        return int(raw) if isinstance(raw, (int, float)) and raw >= 0 else None

    @staticmethod
    def _is_correct_diagnosis(action: Action) -> bool:
        parameters = action.get("parameters", {})
        return (
            ActionSequenceAnalyzer._target(action) == "eq-n1a"
            and isinstance(parameters, Mapping)
            and parameters.get("conclusion") == "fault_detected"
            and parameters.get("reason") == "bearing_wear"
        )

    @staticmethod
    def _is_before(
        first: tuple[int, Action] | None,
        second: tuple[int, Action] | None,
    ) -> bool | None:
        if first is None or second is None:
            return None
        return first[0] < second[0]

    @classmethod
    def _pair_time(cls, pair: tuple[int, Action] | None) -> int | None:
        return cls._time(pair[1]) if pair is not None else None

    @classmethod
    def _max_pair_time(cls, pairs: Sequence[tuple[int, Action]]) -> int | None:
        times = [cls._pair_time(item) for item in pairs]
        known = [item for item in times if item is not None]
        return max(known) if known else None

    @classmethod
    def _latest_time(
        cls,
        first: tuple[int, Action] | None,
        second: tuple[int, Action] | None,
    ) -> int | None:
        return cls._max_pair_time([item for item in (first, second) if item is not None])

    @classmethod
    def _presence(
        cls,
        pair: tuple[int, Action] | None,
        present: str,
        missing: str,
    ) -> str:
        time_ms = cls._pair_time(pair)
        return (
            f"{present} в {cls._format_time(time_ms)} учебного времени"
            if time_ms is not None
            else missing
        )

    @staticmethod
    def _format_time(time_ms: int) -> str:
        total_seconds = time_ms // 1000
        return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"

    @staticmethod
    def _stage(
        stage_id: str,
        title: str,
        status: str,
        completed_at_ms: int | None,
        observations: list[str],
        source_refs: list[str],
    ) -> dict[str, Any]:
        return {
            "stageId": stage_id,
            "title": title,
            "status": status,
            "completedAtMs": completed_at_ms,
            "observations": observations,
            "sourceRefs": source_refs,
        }

    @classmethod
    def _timeline_item(cls, sequence: int, action: Action) -> dict[str, Any]:
        action_type = cls._type(action)
        target = cls._target(action) or None
        raw_sequence = action.get("sequenceNo", sequence)
        sequence_no = int(raw_sequence) if isinstance(raw_sequence, (int, float)) else sequence
        raw_errors = action.get("errorCodes", [])
        error_codes = (
            list(raw_errors)
            if isinstance(raw_errors, Sequence) and not isinstance(raw_errors, (str, bytes))
            else []
        )
        descriptions = {
            "open_equipment_card": "Открыта карточка учебного компонента",
            "view_signal": "Просмотрен учебный сигнал",
            "run_diagnostics": "Запущена учебная диагностика",
            "submit_diagnosis": "Зафиксирован учебный диагноз",
            "start_pump": "Запуск насоса в учебной модели",
            "stop_pump": "Остановка насоса в учебной модели",
            "acknowledge_event": "Подтверждено учебное событие",
            "submit_decision": "Зафиксировано учебное решение",
        }
        return {
            "sequence": sequence_no,
            "virtualTimeMs": cls._time(action),
            "time": (
                cls._format_time(cls._time(action))
                if cls._time(action) is not None
                else None
            ),
            "actionType": action_type,
            "targetId": target,
            "description": descriptions.get(action_type, "Зафиксировано учебное действие"),
            "errorCodes": error_codes,
        }
