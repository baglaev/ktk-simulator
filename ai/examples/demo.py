"""Run with: python3 -m ai.examples.demo"""

from __future__ import annotations

import json

from ai.contracts import HintContext
from ai.hint_engine import HintEngine
from ai.report_builder import SessionReportBuilder


def main() -> None:
    snapshot = {
        "sessionId": "demo-session",
        "mode": "training",
        "timing": {"elapsedMs": 12_000},
        "components": [
            {
                "componentId": "eq-n1a",
                "status": "warning",
                "operatingState": "running",
                "parameters": [
                    {"parameterId": "temperature", "valuePercent": 68, "status": "warning"}
                ],
            },
            {"componentId": "eq-n1b", "status": "success", "operatingState": "stopped"},
        ],
    }
    context = HintContext.from_payload(snapshot)
    hint = HintEngine().evaluate(context)
    print("LIVE HINT")
    print(json.dumps(hint.to_payload(context) if hint else None, ensure_ascii=False, indent=2))

    report = SessionReportBuilder().build(
        session_id="demo-session",
        result={
            "outcome": "failed",
            "errors": ["pra_not_checked", "completed_before_stable"],
            "sections": {"diagnosis": 50, "stabilization": 0},
        },
        actions=[{"actionType": "open_equipment_card", "targetId": "eq-n1a"}],
        issued_hints=[hint.to_payload(context)] if hint else [],
    )
    print("\nPOST-SESSION REPORT")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
