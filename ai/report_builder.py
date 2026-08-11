"""Deterministic post-session analysis for the AI MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .action_analysis import ActionSequenceAnalyzer


class SessionReportBuilder:
    """Build an explainable report without an LLM call."""

    def __init__(
        self,
        rules_path: str | Path | None = None,
        action_analyzer: ActionSequenceAnalyzer | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else Path(__file__).parent / "data" / "report_rules.json"
        with path.open(encoding="utf-8") as source:
            catalog = json.load(source)
        self._rules: Mapping[str, Mapping[str, str]] = catalog["errors"]
        self._action_analyzer = action_analyzer or ActionSequenceAnalyzer()

    def build(
        self,
        *,
        session_id: str,
        result: Mapping[str, Any],
        actions: Sequence[Mapping[str, Any]] = (),
        issued_hints: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        outcome = str(result.get("outcome", result.get("status", "unknown")))
        error_codes = self._extract_error_codes(result)
        mistakes = []
        recommendations: list[str] = []
        for code in error_codes:
            rule = self._rules.get(code)
            if rule is None:
                description = f"Зафиксирована ошибка сценария: {code}."
                recommendation = "Разберите последовательность действий вместе с инструктором."
            else:
                description = rule["description"]
                recommendation = rule["recommendation"]
            mistakes.append({"code": code, "description": description})
            if recommendation not in recommendations:
                recommendations.append(recommendation)

        action_analysis = self._action_analyzer.analyze(actions, result)
        strengths = self._strengths(result, outcome)
        for message in action_analysis["strengths"]:
            if message not in strengths:
                strengths.append(message)
        for message in action_analysis["focusAreas"]:
            if message not in recommendations:
                recommendations.append(message)
        if not recommendations and outcome in {"success", "completed", "passed"}:
            recommendations.append("Закрепите правильную последовательность повторным прохождением без подсказок.")

        return {
            "type": "ai.report",
            "sessionId": session_id,
            "summary": self._summary(outcome, len(mistakes)),
            "outcome": outcome,
            "strengths": strengths,
            "mistakes": mistakes,
            "recommendations": recommendations,
            "metrics": {
                "actionCount": len(actions),
                "hintCount": len(issued_hints),
            },
            "sessionContext": self._session_context(result),
            "actionAnalysis": action_analysis,
            "hintTimeline": self._hint_timeline(issued_hints),
            "provenance": {
                "method": "deterministic_template",
                "llmUsed": False,
                "sourceRefs": ["A-18", "учебное допущение"],
            },
        }

    @staticmethod
    def _session_context(result: Mapping[str, Any]) -> dict[str, Any]:
        """Select factual result data without session or user identifiers."""

        raw_tasks = result.get("taskExecution", result.get("task_execution", []))
        tasks = []
        if isinstance(raw_tasks, Sequence) and not isinstance(
            raw_tasks, (str, bytes)
        ):
            for item in raw_tasks[:20]:
                if not isinstance(item, Mapping):
                    continue
                tasks.append(
                    {
                        "taskId": item.get("taskId", item.get("task_id")),
                        "title": item.get("title"),
                        "status": item.get("status"),
                        "completedAtMs": item.get(
                            "completedAtMs", item.get("completed_at_ms")
                        ),
                        "description": item.get("description"),
                    }
                )

        raw_parameters = result.get(
            "controlledParameters",
            result.get("controlled_parameters", []),
        )
        parameters = []
        if isinstance(raw_parameters, Sequence) and not isinstance(
            raw_parameters, (str, bytes)
        ):
            for item in raw_parameters[:50]:
                if not isinstance(item, Mapping):
                    continue
                parameters.append(
                    {
                        "parameterId": item.get(
                            "parameterId", item.get("parameter_id")
                        ),
                        "name": item.get("name"),
                        "finalValue": item.get(
                            "finalValue", item.get("final_value")
                        ),
                        "minimumValue": item.get(
                            "minimumValue", item.get("minimum_value")
                        ),
                        "unit": item.get("unit"),
                        "status": item.get("status"),
                    }
                )

        raw_critical = result.get(
            "criticalFailureReasons",
            result.get("critical_failure_reasons", []),
        )
        critical_reasons = (
            [str(item) for item in raw_critical[:20]]
            if isinstance(raw_critical, Sequence)
            and not isinstance(raw_critical, (str, bytes))
            else []
        )
        return {
            "outcome": result.get("outcome"),
            "resultStatus": result.get("status", result.get("resultStatus")),
            "mode": result.get("mode"),
            "completionReason": result.get(
                "completionReason", result.get("completion_reason")
            ),
            "elapsedTimeMs": result.get(
                "elapsedTimeMs", result.get("elapsed_time_ms")
            ),
            "totalScore": result.get("totalScore", result.get("total_score")),
            "taskExecution": tasks,
            "controlledParameters": parameters,
            "criticalFailureReasons": critical_reasons,
        }

    @staticmethod
    def _hint_timeline(
        issued_hints: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build a bounded, anonymized timeline of hints actually issued."""

        timeline: list[dict[str, Any]] = []
        for item in issued_hints[:50]:
            if not isinstance(item, Mapping):
                continue
            raw_evidence = item.get("evidence", [])
            evidence = []
            if isinstance(raw_evidence, Sequence) and not isinstance(
                raw_evidence, (str, bytes)
            ):
                for fact in raw_evidence[:10]:
                    if not isinstance(fact, Mapping):
                        continue
                    evidence.append(
                        {
                            "kind": fact.get("kind"),
                            "refId": fact.get("refId", fact.get("ref_id")),
                            "fact": fact.get("fact"),
                        }
                    )
            timeline.append(
                {
                    "hintId": item.get("hintId", item.get("hint_id")),
                    "virtualTimeMs": item.get(
                        "virtualTimeMs", item.get("virtual_time_ms")
                    ),
                    "level": item.get("level"),
                    "title": item.get("title"),
                    "message": item.get("message"),
                    "evidence": evidence,
                }
            )
        return timeline

    @staticmethod
    def _extract_error_codes(result: Mapping[str, Any]) -> list[str]:
        raw_errors = result.get("errors", result.get("errorCodes", ()))
        if not isinstance(raw_errors, Sequence) or isinstance(raw_errors, (str, bytes)):
            raw_errors = ()
        codes: list[str] = []
        for item in raw_errors:
            code = str(item.get("code", "")) if isinstance(item, Mapping) else str(item)
            if code and code not in codes:
                codes.append(code)
        return codes

    @staticmethod
    def _score(result: Mapping[str, Any], *keys: str) -> float | None:
        sections = result.get("sections", result.get("scores", {}))
        if not isinstance(sections, Mapping):
            sections = {}
        for key in keys:
            raw = result.get(key, sections.get(key))
            if isinstance(raw, Mapping):
                score = raw.get("score", raw.get("value"))
                maximum = raw.get("maxScore", raw.get("max_score"))
                if score is not None and maximum is not None and float(maximum) > 0:
                    return float(score) / float(maximum) * 100
                raw = score
            if raw is not None:
                return float(raw)
        return None

    def _strengths(self, result: Mapping[str, Any], outcome: str) -> list[str]:
        strengths: list[str] = []
        if outcome in {"success", "completed", "passed"}:
            strengths.append("Сценарий завершен с успешным учебным результатом.")
        checks = (
            (("diagnosis", "diagnostics"), "Учебная неисправность распознана корректно."),
            (
                ("stabilization", "recovery"),
                "Учебное переключение насосов выполнено по критериям оценки.",
            ),
            (
                ("consequenceControl", "consequence_control", "consequences", "safety"),
                "Последствия развития отказа были ограничены.",
            ),
            (("timeliness", "time"), "Ключевые действия выполнены своевременно."),
        )
        for keys, message in checks:
            score = self._score(result, *keys)
            if score is not None and score >= 100:
                strengths.append(message)
        return strengths

    @staticmethod
    def _summary(outcome: str, mistake_count: int) -> str:
        if outcome in {"success", "completed", "passed"}:
            return "Сценарий пройден успешно; сформирован учебный разбор действий."
        if outcome in {"failed", "failure"}:
            return f"Сценарий не пройден; найдено ошибок: {mistake_count}."
        return f"Сценарий завершен со статусом «{outcome}»; найдено ошибок: {mistake_count}."
