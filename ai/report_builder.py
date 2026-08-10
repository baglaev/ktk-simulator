"""Deterministic post-session analysis for the AI MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


class SessionReportBuilder:
    """Build an explainable report without an LLM call."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        path = Path(rules_path) if rules_path else Path(__file__).parent / "data" / "report_rules.json"
        with path.open(encoding="utf-8") as source:
            catalog = json.load(source)
        self._rules: Mapping[str, Mapping[str, str]] = catalog["errors"]

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

        strengths = self._strengths(result, outcome)
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
            "provenance": {
                "method": "deterministic_template",
                "llmUsed": False,
                "sourceRefs": ["A-18", "учебное допущение"],
            },
        }

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
            (("stabilization", "recovery"), "Стабилизация после переключения подтверждена."),
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
