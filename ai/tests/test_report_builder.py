from __future__ import annotations

import json
import unittest

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


if __name__ == "__main__":
    unittest.main()
