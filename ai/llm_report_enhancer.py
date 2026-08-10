"""Optional LLM enhancement for a deterministic post-session report."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .openai_compatible import (
    LLMConfigurationError,
    LLMError,
    LLMResponseError,
    OpenAICompatibleClient,
    parse_json_object,
)


_SYSTEM_PROMPT = """Отредактируй учебный отчет КТК ЭЛОУ-АВТ на русском языке.
Используй только факты deterministicReport и actionAnalysis. Не вычисляй новые
времена, оценки или причинно-следственные связи. Не добавляй производственные
команды, уставки, нормативы или физические единицы. Все времена относятся только
к учебной модели. Сохрани порядок и количество strengths, mistakes и
recommendations; коды ошибок не изменяй.
Верни только JSON: summary — строка; strengths и recommendations — массивы строк;
mistakes — массив объектов {code, description}.
"""


class LLMReportEnhancer:
    """Improve wording once after a session, with a safe fallback on any error."""

    def __init__(self, client: OpenAICompatibleClient | None = None) -> None:
        self._client = client or OpenAICompatibleClient()

    def enhance(
        self,
        report: Mapping[str, Any],
        *,
        actions: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        fallback = deepcopy(dict(report))
        try:
            completion = self._client.complete_json(
                system_prompt=_SYSTEM_PROMPT,
                user_payload=self._prompt_payload(report),
            )
            candidate = parse_json_object(completion.content)
            self._validate_candidate(candidate, report)
        except LLMError as error:
            self._mark_fallback(fallback, error)
            return fallback

        enhanced = deepcopy(dict(report))
        enhanced["summary"] = candidate["summary"]
        enhanced["strengths"] = candidate["strengths"]
        enhanced["mistakes"] = candidate["mistakes"]
        enhanced["recommendations"] = candidate["recommendations"]
        provenance = dict(enhanced.get("provenance", {}))
        provenance.update(
            {
                "method": "deterministic_plus_llm",
                "llmAttempted": True,
                "llmUsed": True,
                "requestedModel": completion.requested_model,
                "resolvedModel": completion.resolved_model,
                "usage": dict(completion.usage),
            }
        )
        enhanced["provenance"] = provenance
        return enhanced

    @staticmethod
    def _prompt_payload(
        report: Mapping[str, Any],
    ) -> dict[str, Any]:
        raw_analysis = report.get("actionAnalysis", {})
        analysis = raw_analysis if isinstance(raw_analysis, Mapping) else {}
        raw_stages = analysis.get("stages", [])
        stages = []
        if isinstance(raw_stages, Sequence) and not isinstance(raw_stages, (str, bytes)):
            for item in raw_stages:
                if isinstance(item, Mapping):
                    stages.append(
                        {
                            "stageId": item.get("stageId"),
                            "status": item.get("status"),
                            "completedAtMs": item.get("completedAtMs"),
                            "observations": item.get("observations", []),
                        }
                    )
        return {
            "deterministicReport": {
                "outcome": report.get("outcome"),
                "summary": report.get("summary"),
                "strengths": report.get("strengths", []),
                "mistakes": report.get("mistakes", []),
                "recommendations": report.get("recommendations", []),
            },
            "actionAnalysis": {
                "stages": stages,
                "timing": analysis.get("timing", {}),
                "sequence": analysis.get("sequence", {}),
                "focusAreas": analysis.get("focusAreas", []),
            },
        }

    @staticmethod
    def _validate_candidate(
        candidate: Mapping[str, Any],
        original: Mapping[str, Any],
    ) -> None:
        if not isinstance(candidate.get("summary"), str):
            raise LLMResponseError("LLM report summary must be a string")
        for field in ("strengths", "recommendations"):
            value = candidate.get(field)
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise LLMResponseError(f"LLM report {field} must be a string list")
            original_value = original.get(field, [])
            if len(value) != len(original_value):
                raise LLMResponseError(f"LLM changed deterministic {field} count")
        mistakes = candidate.get("mistakes")
        if not isinstance(mistakes, list) or not all(
            isinstance(item, Mapping)
            and isinstance(item.get("code"), str)
            and isinstance(item.get("description"), str)
            for item in mistakes
        ):
            raise LLMResponseError("LLM report mistakes have an invalid format")
        original_codes = [item.get("code") for item in original.get("mistakes", [])]
        candidate_codes = [item.get("code") for item in mistakes]
        if candidate_codes != original_codes:
            raise LLMResponseError("LLM changed deterministic error codes")

    @staticmethod
    def _mark_fallback(report: dict[str, Any], error: LLMError) -> None:
        attempted = not isinstance(error, LLMConfigurationError)
        provenance = dict(report.get("provenance", {}))
        provenance.update(
            {
                "llmAttempted": attempted,
                "llmUsed": False,
                "llmStatus": "fallback" if attempted else "disabled",
                "llmError": type(error).__name__,
                "llmErrorMessage": str(error),
            }
        )
        report["provenance"] = provenance
