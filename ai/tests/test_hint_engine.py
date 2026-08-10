from __future__ import annotations

import json
import unittest

from ai.contracts import HintContext
from ai.hint_engine import HintEngine


def snapshot(
    *,
    n1a_status: str = "success",
    n1a_state: str = "running",
    n1b_state: str = "stopped",
    discharge_state: dict | None = None,
    mode: str = "training",
) -> dict:
    components = [
        {
            "componentId": "eq-n1a",
            "status": n1a_status,
            "operatingState": n1a_state,
            "parameters": [],
        },
        {
            "componentId": "eq-n1b",
            "status": "success",
            "operatingState": n1b_state,
            "parameters": [],
        },
    ]
    if discharge_state is not None:
        components.append(
            {
                "componentId": "eq-n1-discharge",
                "status": "success",
                "state": discharge_state,
                "parameters": [],
            }
        )
    return {
        "sessionId": "session-1",
        "mode": mode,
        "timing": {"elapsedMs": 25_000},
        "components": components,
    }


class HintEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = HintEngine()

    def test_normal_state_has_no_hint(self) -> None:
        context = HintContext.from_payload(snapshot())
        self.assertIsNone(self.engine.evaluate(context))

    def test_warning_prompts_to_inspect_n1a(self) -> None:
        context = HintContext.from_payload(snapshot(n1a_status="warning"))
        hint = self.engine.evaluate(context)
        self.assertIsNotNone(hint)
        self.assertEqual(hint.hint_id, "inspect-n1a")

    def test_hint_is_not_repeated_for_session(self) -> None:
        context = HintContext.from_payload(snapshot(n1a_status="warning"))
        self.assertIsNotNone(self.engine.evaluate(context))
        self.assertIsNone(self.engine.evaluate(context))

    def test_control_mode_has_no_hint(self) -> None:
        context = HintContext.from_payload(snapshot(n1a_status="alert", mode="control"))
        self.assertIsNone(self.engine.evaluate(context))

    def test_open_card_prompts_to_compare_signals(self) -> None:
        actions = [{"actionType": "open_equipment_card", "targetId": "eq-n1a"}]
        context = HintContext.from_payload(snapshot(n1a_status="alert"), actions)
        hint = self.engine.evaluate(context)
        self.assertEqual(hint.hint_id, "compare-line-signals")

    def test_viewed_signals_prompt_to_run_diagnostics(self) -> None:
        actions = [
            {"actionType": "open_equipment_card", "targetId": "eq-n1a"},
            {"actionType": "view_signal", "targetId": "PRA351"},
            {"actionType": "view_signal", "targetId": "FYQR117"},
        ]
        context = HintContext.from_payload(snapshot(n1a_status="alert"), actions)
        hint = self.engine.evaluate(context)
        self.assertEqual(hint.hint_id, "run-diagnostics")

    def test_unsafe_switch_has_highest_priority(self) -> None:
        context = HintContext.from_payload(
            snapshot(n1a_status="alert", n1a_state="stopped", n1b_state="stopped")
        )
        hint = self.engine.evaluate(context)
        self.assertEqual(hint.hint_id, "unsafe-pump-configuration")
        self.assertEqual(hint.level, "alert")

    def test_recovery_and_stabilized_hints(self) -> None:
        recovering = HintContext.from_payload(
            snapshot(
                n1a_state="stopped",
                n1b_state="running",
                discharge_state={
                    "safePumpConfiguration": True,
                    "recoveryActive": True,
                    "stabilized": False,
                },
            )
        )
        self.assertEqual(self.engine.evaluate(recovering).hint_id, "monitor-recovery")
        self.engine.reset_session("session-1")
        stable = HintContext.from_payload(
            snapshot(
                n1a_state="stopped",
                n1b_state="running",
                discharge_state={
                    "safePumpConfiguration": True,
                    "recoveryActive": False,
                    "stabilized": True,
                },
            )
        )
        self.assertEqual(self.engine.evaluate(stable).hint_id, "ready-to-complete")

    def test_payload_is_json_serializable(self) -> None:
        context = HintContext.from_payload(snapshot(n1a_status="warning"))
        payload = self.engine.evaluate(context).to_payload(context)
        self.assertEqual(payload["type"], "ai.hint")
        self.assertFalse(payload["provenance"]["llmUsed"])
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
