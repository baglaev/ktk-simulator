from __future__ import annotations

import json
import unittest

from ai.llm_report_enhancer import LLMReportEnhancer
from ai.openai_compatible import CompletionResult, LLMRequestError
from ai.openai_compatible import LLMConfigurationError


def base_report() -> dict:
    return {
        "type": "ai.report",
        "sessionId": "session-1",
        "outcome": "failed",
        "summary": "Исходный итог.",
        "strengths": ["Исходная сильная сторона."],
        "mistakes": [
            {"code": "pra_not_checked", "description": "Исходная ошибка."}
        ],
        "recommendations": ["Исходная рекомендация."],
        "metrics": {"actionCount": 1, "hintCount": 0},
        "sessionContext": {
            "completionReason": "critical_limit_reached",
            "controlledParameters": [
                {
                    "parameterId": "LRCA605",
                    "finalValue": 20,
                    "minimumValue": 20,
                    "unit": "%",
                }
            ],
        },
        "actionAnalysis": {
            "stages": [
                {
                    "stageId": "detection",
                    "status": "warning",
                    "completedAtMs": 20_000,
                    "observations": ["PRA 351 не просмотрен до диагноза"],
                }
            ],
            "timing": {"firstReactionAtMs": 20_000},
            "sequence": {"diagnosisBeforePumpActions": True},
            "timeline": [
                {
                    "sequence": 1,
                    "virtualTimeMs": 20_000,
                    "actionType": "view_signal",
                    "targetId": "FYQR117",
                }
            ],
            "focusAreas": ["Проверить PRA 351 до диагноза"],
        },
        "hintTimeline": [
            {
                "hintId": "compare-line-signals",
                "virtualTimeMs": 15_000,
                "title": "Сравните связанные сигналы",
            }
        ],
        "journalTimeline": [
            {
                "time": "00:20",
                "description": "Просмотрен параметр FYQR 117",
            }
        ],
        "errorAnalysis": [
            {
                "code": "pra_not_checked",
                "detectedAtMs": 42_000,
                "consequence": "Не подтверждено влияние Н-1А на линию",
            }
        ],
        "provenance": {
            "method": "deterministic_template",
            "llmUsed": False,
            "sourceRefs": ["A-18", "учебное допущение"],
        },
    }


class SuccessfulClient:
    def complete_json(self, *, system_prompt, user_payload):
        assert "производственные" in system_prompt
        assert "sessionId" not in json.dumps(user_payload)
        assert "actionAnalysis" in user_payload
        assert user_payload["actionAnalysis"]["timeline"][0]["targetId"] == (
            "FYQR117"
        )
        assert user_payload["sessionContext"]["controlledParameters"][0][
            "parameterId"
        ] == "LRCA605"
        assert user_payload["hintTimeline"][0]["hintId"] == (
            "compare-line-signals"
        )
        assert user_payload["journalTimeline"][0]["time"] == "00:20"
        assert user_payload["errorAnalysis"][0]["code"] == "pra_not_checked"
        return CompletionResult(
            content=json.dumps(
                {
                    "summary": "Персонализированный учебный итог.",
                    "strengths": ["Неисправность была замечена."],
                    "mistakes": [
                        {
                            "code": "pra_not_checked",
                            "description": "PRA 351 не был проверен до диагноза.",
                        }
                    ],
                    "recommendations": ["Повторите учебный анализ PRA 351."],
                },
                ensure_ascii=False,
            ),
            requested_model="openrouter/free",
            resolved_model="openai/gpt-oss-20b:free",
            usage={"total_tokens": 250},
        )


class FailingClient:
    def complete_json(self, **_kwargs):
        raise LLMRequestError("provider unavailable")


class ChangedFactsClient:
    def complete_json(self, **_kwargs):
        return CompletionResult(
            content=json.dumps(
                {
                    "summary": "Итог",
                    "strengths": [],
                    "mistakes": [],
                    "recommendations": [],
                }
            ),
            requested_model="openrouter/free",
            resolved_model="some-model",
            usage={},
        )


class DisabledClient:
    def complete_json(self, **_kwargs):
        raise LLMConfigurationError("disabled")


class LLMReportEnhancerTests(unittest.TestCase):
    def test_successful_enhancement_preserves_deterministic_fields(self) -> None:
        original = base_report()
        enhanced = LLMReportEnhancer(SuccessfulClient()).enhance(
            original,
            actions=[
                {
                    "actionType": "view_signal",
                    "targetId": "FYQR117",
                    "virtualTimeMs": 20_000,
                }
            ],
        )
        self.assertEqual(enhanced["sessionId"], original["sessionId"])
        self.assertEqual(enhanced["metrics"], original["metrics"])
        self.assertTrue(enhanced["provenance"]["llmUsed"])
        self.assertEqual(
            enhanced["provenance"]["resolvedModel"], "openai/gpt-oss-20b:free"
        )

    def test_provider_failure_returns_deterministic_report(self) -> None:
        original = base_report()
        enhanced = LLMReportEnhancer(FailingClient()).enhance(original)
        self.assertEqual(enhanced["summary"], original["summary"])
        self.assertFalse(enhanced["provenance"]["llmUsed"])
        self.assertEqual(enhanced["provenance"]["llmStatus"], "fallback")
        self.assertEqual(
            enhanced["provenance"]["llmErrorMessage"], "provider unavailable"
        )

    def test_changed_error_codes_are_rejected(self) -> None:
        original = base_report()
        enhanced = LLMReportEnhancer(ChangedFactsClient()).enhance(original)
        self.assertEqual(enhanced["mistakes"], original["mistakes"])
        self.assertEqual(enhanced["provenance"]["llmError"], "LLMResponseError")

    def test_disabled_client_does_not_claim_an_api_attempt(self) -> None:
        enhanced = LLMReportEnhancer(DisabledClient()).enhance(base_report())
        self.assertFalse(enhanced["provenance"]["llmAttempted"])
        self.assertEqual(enhanced["provenance"]["llmStatus"], "disabled")


if __name__ == "__main__":
    unittest.main()
