"""Prepared live hints for the educational MVP scenario.

No LLM or network call is made here.  The engine evaluates cheap deterministic
rules and emits at most one new hint for each invocation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .contracts import (
    ActionObservation,
    ComponentObservation,
    Hint,
    HintContext,
    HintEvidence,
)


RuleResult = tuple[HintEvidence, ...] | None


class HintEngine:
    """Select a prepared hint from current telemetry and action history."""

    def __init__(self, catalog_path: str | Path | None = None) -> None:
        path = Path(catalog_path) if catalog_path else Path(__file__).parent / "data" / "hints.json"
        with path.open(encoding="utf-8") as source:
            catalog = json.load(source)
        self._rules: list[Mapping[str, Any]] = sorted(
            catalog["rules"], key=lambda item: int(item["priority"]), reverse=True
        )
        self._emitted_by_session: dict[str, set[str]] = {}
        self._evaluators: dict[str, Callable[[HintContext], RuleResult]] = {
            "unsafe_switch": self._unsafe_switch,
            "ready_to_complete": self._ready_to_complete,
            "monitor_recovery": self._monitor_recovery,
            "review_switch": self._review_switch,
            "submit_diagnosis": self._submit_diagnosis,
            "run_diagnostics": self._run_diagnostics,
            "compare_line_signals": self._compare_line_signals,
            "inspect_n1a": self._inspect_n1a,
        }

    def evaluate(self, context: HintContext) -> Hint | None:
        """Return the highest-priority new hint, or ``None``.

        Hints are disabled in control mode and deduplicated per session.
        """

        if context.mode.lower() == "control":
            return None

        emitted = self._emitted_by_session.setdefault(context.session_id, set())
        for rule in self._rules:
            hint_id = str(rule["hintId"])
            if hint_id in emitted:
                continue
            evidence = self._evaluators[str(rule["ruleId"])](context)
            if evidence is None:
                continue
            emitted.add(hint_id)
            return Hint(
                hint_id=hint_id,
                level=str(rule["level"]),
                title=str(rule["title"]),
                message=str(rule["message"]),
                evidence=evidence,
                source_refs=tuple(str(item) for item in rule["sourceRefs"]),
            )
        return None

    def reset_session(self, session_id: str) -> None:
        self._emitted_by_session.pop(session_id, None)

    @staticmethod
    def _component(context: HintContext, component_id: str) -> ComponentObservation | None:
        normalized = component_id.lower().replace("-", "")
        for component in context.components:
            candidate = component.component_id.lower().replace("-", "")
            if candidate == normalized:
                return component
        return None

    @staticmethod
    def _has_action(
        actions: tuple[ActionObservation, ...],
        action_type: str,
        target_ids: set[str] | None = None,
    ) -> bool:
        normalized_targets = (
            {item.lower().replace("-", "") for item in target_ids}
            if target_ids
            else None
        )
        for action in actions:
            if action.action_type != action_type:
                continue
            if normalized_targets is None:
                return True
            target = (action.target_id or "").lower().replace("-", "")
            if target in normalized_targets:
                return True
        return False

    @staticmethod
    def _is_running(component: ComponentObservation | None) -> bool:
        if component is None:
            return False
        value = (component.operating_state or component.state.get("operatingState", "")).lower()
        return value in {"running", "started", "on", "active"}

    @classmethod
    def _safe_pump_configuration(cls, context: HintContext) -> bool:
        discharge = cls._component(context, "eq-n1-discharge")
        if discharge is not None and "safePumpConfiguration" in discharge.state:
            return bool(discharge.state["safePumpConfiguration"])
        return cls._is_running(cls._component(context, "eq-n1b")) and not cls._is_running(
            cls._component(context, "eq-n1a")
        )

    @staticmethod
    def _correct_diagnosis(actions: tuple[ActionObservation, ...]) -> bool:
        for action in actions:
            if action.action_type != "submit_diagnosis":
                continue
            if (action.target_id or "").lower().replace("-", "") != "eqn1a":
                continue
            if (
                action.parameters.get("conclusion") == "fault_detected"
                and action.parameters.get("reason") == "bearing_wear"
            ):
                return True
        return False

    def _unsafe_switch(self, context: HintContext) -> RuleResult:
        n1a = self._component(context, "eq-n1a")
        n1b = self._component(context, "eq-n1b")
        if not self._is_running(n1a) and not self._is_running(n1b):
            return (
                HintEvidence("component", "eq-n1a", "Н-1А не работает"),
                HintEvidence("component", "eq-n1b", "Н-1Б не работает"),
            )
        return None

    def _inspect_n1a(self, context: HintContext) -> RuleResult:
        n1a = self._component(context, "eq-n1a")
        if n1a is None or n1a.status not in {"warning", "alert"}:
            return None
        if self._has_action(context.actions, "open_equipment_card", {"eq-n1a"}):
            return None
        return (HintEvidence("component", "eq-n1a", f"Статус Н-1А: {n1a.status}"),)

    def _compare_line_signals(self, context: HintContext) -> RuleResult:
        n1a = self._component(context, "eq-n1a")
        if n1a is None or n1a.status not in {"warning", "alert"}:
            return None
        if not self._has_action(context.actions, "open_equipment_card", {"eq-n1a"}):
            return None
        missing = []
        if not self._has_action(context.actions, "view_signal", {"PRA351", "PRA-351"}):
            missing.append("PRA 351")
        if not self._has_action(context.actions, "view_signal", {"FYQR117", "FYQR-117"}):
            missing.append("FYQR 117")
        if not missing:
            return None
        return (
            HintEvidence("action", "view_signal", f"Не просмотрены сигналы: {', '.join(missing)}"),
        )

    def _run_diagnostics(self, context: HintContext) -> RuleResult:
        viewed_pra = self._has_action(context.actions, "view_signal", {"PRA351", "PRA-351"})
        viewed_fyqr = self._has_action(context.actions, "view_signal", {"FYQR117", "FYQR-117"})
        if not (viewed_pra and viewed_fyqr):
            return None
        if self._has_action(context.actions, "run_diagnostics") or self._has_action(
            context.actions, "submit_diagnosis"
        ):
            return None
        return (
            HintEvidence("action", "view_signal", "PRA 351 и FYQR 117 просмотрены"),
        )

    def _submit_diagnosis(self, context: HintContext) -> RuleResult:
        if not self._has_action(context.actions, "run_diagnostics"):
            return None
        if self._has_action(context.actions, "submit_diagnosis"):
            return None
        return (HintEvidence("action", "run_diagnostics", "Диагностика выполнена"),)

    def _review_switch(self, context: HintContext) -> RuleResult:
        if not self._correct_diagnosis(context.actions):
            return None
        if self._safe_pump_configuration(context):
            return None
        return (
            HintEvidence("action", "submit_diagnosis", "Учебная неисправность определена"),
            HintEvidence("component", "eq-n1-discharge", "Резервирование не подтверждено"),
        )

    def _monitor_recovery(self, context: HintContext) -> RuleResult:
        discharge = self._component(context, "eq-n1-discharge")
        if discharge is None:
            return None
        if not bool(discharge.state.get("recoveryActive")):
            return None
        if bool(discharge.state.get("stabilized")):
            return None
        return (
            HintEvidence("component", "eq-n1-discharge", "Идет учебное восстановление параметров"),
        )

    def _ready_to_complete(self, context: HintContext) -> RuleResult:
        discharge = self._component(context, "eq-n1-discharge")
        if discharge is None or not bool(discharge.state.get("stabilized")):
            return None
        if self._has_action(context.actions, "complete_scenario"):
            return None
        return (
            HintEvidence("component", "eq-n1-discharge", "Учебная модель подтверждает стабилизацию"),
        )
