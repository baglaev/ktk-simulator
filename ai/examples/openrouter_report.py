"""Generate one post-session report through an OpenAI-compatible provider.

Run from the repository root after exporting variables from ``ai/.env``:
``python3 -m ai.examples.openrouter_report``.
"""

from __future__ import annotations

import json

from ai.llm_report_enhancer import LLMReportEnhancer
from ai.openai_compatible import LLMConfig, OpenAICompatibleClient
from ai.report_builder import SessionReportBuilder


def main() -> None:
    actions = [
        {
            "virtualTimeMs": 30_000,
            "actionType": "open_equipment_card",
            "targetId": "eq-n1a",
        },
        {
            "virtualTimeMs": 38_000,
            "actionType": "view_signal",
            "targetId": "FYQR117",
        },
        {
            "virtualTimeMs": 50_000,
            "actionType": "submit_diagnosis",
            "targetId": "eq-n1a",
            "parameters": {
                "conclusion": "fault_detected",
                "reason": "bearing_wear",
            },
        },
        {
            "virtualTimeMs": 60_000,
            "actionType": "start_pump",
            "targetId": "eq-n1b",
        },
        {
            "virtualTimeMs": 65_000,
            "actionType": "stop_pump",
            "targetId": "eq-n1a",
        },
        {
            "virtualTimeMs": 70_000,
            "actionType": "open_equipment_card",
            "targetId": "eq-elou",
        },
    ]
    base_report = SessionReportBuilder().build(
        session_id="openrouter-demo",
        result={
            "outcome": "failed",
            "errorCodes": [
                "pra_not_checked",
                "e15_not_checked_after_switch",
                "lrca_recovery_not_confirmed",
                "completed_before_stable"
            ],
            "criticalFailureReasons": [
                "Сценарий завершён до стабилизации параметров"
            ],
            "diagnosis": {"score": 22, "maxScore": 25},
            "stabilization": {"score": 40, "maxScore": 40},
            "consequenceControl": {"score": 8, "maxScore": 20},
            "timeliness": {"score": 15, "maxScore": 15},
        },
        actions=actions,
    )
    config = LLMConfig.from_env()
    enhanced = LLMReportEnhancer(OpenAICompatibleClient(config)).enhance(
        base_report,
        actions=actions,
    )
    print(json.dumps(enhanced, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
