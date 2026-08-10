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
            "virtualTimeMs": 90_000,
            "actionType": "submit_diagnosis",
            "targetId": "eq-n1a",
            "parameters": {
                "conclusion": "fault_detected",
                "reason": "bearing_wear",
            },
        },
    ]
    base_report = SessionReportBuilder().build(
        session_id="openrouter-demo",
        result={
            "outcome": "failed",
            "errorCodes": ["pra_not_checked", "completed_before_stable"],
            "diagnosis": {"score": 20, "maxScore": 35},
            "stabilization": {"score": 0, "maxScore": 30},
            "consequenceControl": {"score": 10, "maxScore": 20},
            "timeliness": {"score": 5, "maxScore": 15},
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
