from __future__ import annotations

import json
import unittest

from ai.action_analysis import ActionSequenceAnalyzer


def action(time_ms: int, action_type: str, target_id: str, **parameters) -> dict:
    payload = {
        "virtualTimeMs": time_ms,
        "actionType": action_type,
        "targetId": target_id,
    }
    if parameters:
        payload["parameters"] = parameters
    return payload


def successful_actions() -> list[dict]:
    return [
        action(15_000, "open_equipment_card", "eq-n1a"),
        action(20_000, "view_signal", "PRA351"),
        action(22_000, "view_signal", "FYQR117"),
        action(30_000, "run_diagnostics", "eq-n1a"),
        action(
            35_000,
            "submit_diagnosis",
            "eq-n1a",
            conclusion="fault_detected",
            reason="bearing_wear",
        ),
        action(40_000, "start_pump", "eq-n1b"),
        action(45_000, "stop_pump", "eq-n1a"),
        action(50_000, "view_signal", "PRA351"),
        action(51_000, "view_signal", "FYQR117"),
        action(52_000, "open_equipment_card", "eq-elou"),
        action(53_000, "open_equipment_card", "eq-e15"),
        action(54_000, "view_signal", "LRCA605"),
    ]


class ActionSequenceAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = ActionSequenceAnalyzer()

    def test_complete_sequence_marks_all_stages_success(self) -> None:
        analysis = self.analyzer.analyze(
            successful_actions(),
            {"outcome": "success", "errorCodes": []},
        )
        statuses = {item["stageId"]: item["status"] for item in analysis["stages"]}
        self.assertEqual(set(statuses.values()), {"success"})
        self.assertEqual(analysis["timing"]["firstReactionDelayMs"], 5_000)
        self.assertEqual(analysis["timing"]["correctDiagnosisAtMs"], 35_000)
        self.assertEqual(analysis["timing"]["switchCompletedAtMs"], 45_000)
        self.assertEqual(analysis["timeline"][0]["time"], "00:15")
        self.assertTrue(analysis["sequence"]["diagnosisBeforePumpActions"])
        self.assertTrue(
            analysis["sequence"]["reserveStartedBeforeFaultyPumpStopped"]
        )
        self.assertEqual(analysis["focusAreas"], [])
        self.assertGreaterEqual(len(analysis["strengths"]), 4)

    def test_partial_sequence_identifies_specific_gaps(self) -> None:
        actions = [
            action(20_000, "open_equipment_card", "eq-n1a"),
            action(
                50_000,
                "submit_diagnosis",
                "eq-n1a",
                conclusion="fault_detected",
                reason="bearing_wear",
            ),
            action(60_000, "start_pump", "eq-n1b"),
            action(65_000, "stop_pump", "eq-n1a"),
            action(70_000, "open_equipment_card", "eq-elou"),
        ]
        analysis = self.analyzer.analyze(actions, {"outcome": "failed"})
        statuses = {item["stageId"]: item["status"] for item in analysis["stages"]}
        self.assertEqual(statuses["detection"], "warning")
        self.assertEqual(statuses["diagnosis"], "success")
        self.assertEqual(statuses["switching"], "success")
        self.assertEqual(statuses["recovery_control"], "warning")
        joined = " ".join(analysis["focusAreas"])
        self.assertIn("PRA 351", joined)
        self.assertIn("LRCA 605", joined)
        self.assertIn("стабилизацию", joined)

    def test_reversed_pump_sequence_is_warning(self) -> None:
        actions = [
            action(
                30_000,
                "submit_diagnosis",
                "eq-n1a",
                conclusion="fault_detected",
                reason="bearing_wear",
            ),
            action(40_000, "stop_pump", "eq-n1a"),
            action(45_000, "start_pump", "eq-n1b"),
        ]
        analysis = self.analyzer.analyze(actions, {"outcome": "failed"})
        switching = next(
            item for item in analysis["stages"] if item["stageId"] == "switching"
        )
        self.assertEqual(switching["status"], "warning")
        self.assertFalse(
            analysis["sequence"]["reserveStartedBeforeFaultyPumpStopped"]
        )

    def test_empty_action_list_is_explainable_and_serializable(self) -> None:
        analysis = self.analyzer.analyze([], {"outcome": "failed"})
        self.assertEqual(analysis["timeline"], [])
        self.assertIsNone(analysis["timing"]["firstReactionAtMs"])
        self.assertTrue(analysis["focusAreas"])
        self.assertEqual(analysis["provenance"]["method"], "deterministic_action_analysis")
        json.dumps(analysis)

    def test_optional_action_fields_do_not_break_timeline(self) -> None:
        analysis = self.analyzer.analyze(
            [
                {
                    "sequenceNo": None,
                    "virtualTimeMs": 12_000,
                    "actionType": "acknowledge_event",
                    "targetId": None,
                    "errorCodes": None,
                }
            ],
            {"outcome": "failed"},
        )
        self.assertEqual(analysis["timeline"][0]["sequence"], 1)
        self.assertIsNone(analysis["timeline"][0]["targetId"])
        self.assertEqual(analysis["timeline"][0]["errorCodes"], [])


if __name__ == "__main__":
    unittest.main()
