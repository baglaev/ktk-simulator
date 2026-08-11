from __future__ import annotations

import json
import unittest

from ai.tests.test_action_analysis import successful_actions
from ai.report_builder import SessionReportBuilder


class SessionReportBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = SessionReportBuilder()

    def test_success_report_contains_strengths(self) -> None:
        report = self.builder.build(
            session_id="success-session",
            result={
                "outcome": "success",
                "totalScore": 100,
                "diagnosis": {"score": 35, "maxScore": 35},
                "stabilization": {"score": 30, "maxScore": 30},
                "consequenceControl": {"score": 20, "maxScore": 20},
                "timeliness": {"score": 15, "maxScore": 15},
                "errorCodes": [],
            },
        )
        self.assertEqual(report["mistakes"], [])
        self.assertGreaterEqual(len(report["strengths"]), 5)
        self.assertFalse(report["provenance"]["llmUsed"])

    def test_normalized_hundred_point_sections_are_recognized(self) -> None:
        report = self.builder.build(
            session_id="normalized-session",
            result={
                "outcome": "success",
                "sections": {
                    "diagnosis": 100,
                    "stabilization": 100,
                    "consequences": 100,
                    "timeliness": 100,
                },
            },
        )
        self.assertGreaterEqual(len(report["strengths"]), 5)

    def test_failed_report_maps_known_errors(self) -> None:
        report = self.builder.build(
            session_id="failed-session",
            result={
                "outcome": "failed",
                "errors": ["pra_not_checked", {"code": "completed_before_stable"}],
            },
            actions=[{"actionType": "complete_scenario"}],
        )
        self.assertEqual(len(report["mistakes"]), 2)
        self.assertEqual(report["metrics"]["actionCount"], 1)
        self.assertTrue(report["recommendations"])

    def test_unknown_error_has_safe_fallback(self) -> None:
        report = self.builder.build(
            session_id="unknown-session",
            result={"outcome": "failed", "errors": ["future_error"]},
        )
        self.assertEqual(report["mistakes"][0]["code"], "future_error")
        self.assertIn("инструктором", report["recommendations"][0])

    def test_report_is_json_serializable(self) -> None:
        report = self.builder.build(
            session_id="json-session",
            result={"status": "completed", "errorCodes": []},
            issued_hints=[{"hintId": "inspect-n1a"}],
        )
        self.assertEqual(report["type"], "ai.report")
        self.assertEqual(report["metrics"]["hintCount"], 1)
        json.dumps(report)

    def test_report_contains_deterministic_action_analysis(self) -> None:
        actions = successful_actions()
        report = self.builder.build(
            session_id="analyzed-session",
            result={"outcome": "success", "errorCodes": []},
            actions=actions,
        )
        self.assertEqual(report["metrics"]["actionCount"], len(actions))
        self.assertEqual(
            report["actionAnalysis"]["timing"]["switchCompletedAtMs"], 45_000
        )
        self.assertIn(
            "правильной последовательности",
            " ".join(report["strengths"]),
        )

    def test_report_contains_anonymized_session_and_hint_context(self) -> None:
        report = self.builder.build(
            session_id="private-session-id",
            result={
                "outcome": "failed",
                "status": "failed",
                "completionReason": "critical_limit_reached",
                "elapsedTimeMs": 120_000,
                "totalScore": 42,
                "taskExecution": [
                    {
                        "taskId": "diagnosis",
                        "title": "Диагностика Н-1А",
                        "status": "success",
                        "completedAtMs": 35_000,
                        "description": "Корректный диагноз зафиксирован",
                    }
                ],
                "controlledParameters": [
                    {
                        "parameterId": "LRCA605",
                        "name": "Уровень Е-15",
                        "finalValue": 20,
                        "minimumValue": 20,
                        "unit": "%",
                        "status": "alert",
                    }
                ],
                "criticalFailureReasons": ["LRCA 605 достиг 20%"],
            },
            issued_hints=[
                {
                    "hintId": "inspect-n1a",
                    "virtualTimeMs": 10_000,
                    "level": "warning",
                    "title": "Проверьте Н-1А",
                    "message": "Откройте карточку Н-1А",
                    "evidence": [
                        {
                            "kind": "component",
                            "refId": "eq-n1a",
                            "fact": "Статус warning",
                        }
                    ],
                }
            ],
        )

        self.assertNotIn("sessionId", report["sessionContext"])
        self.assertEqual(
            report["sessionContext"]["controlledParameters"][0][
                "parameterId"
            ],
            "LRCA605",
        )
        self.assertEqual(report["hintTimeline"][0]["hintId"], "inspect-n1a")
        self.assertEqual(
            report["hintTimeline"][0]["evidence"][0]["refId"],
            "eq-n1a",
        )


if __name__ == "__main__":
    unittest.main()
