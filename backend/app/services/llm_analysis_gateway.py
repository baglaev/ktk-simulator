from __future__ import annotations

import sys
from pathlib import Path

from app.domain import RecordedAction, ScenarioHintMessage, SessionAIAnalysis, SessionResult


class PostSessionLLMAnalysisGateway:
    """Optionally improve wording after deterministic scoring has finished."""

    def __init__(self) -> None:
        self._repository_root = Path(__file__).resolve().parents[3]

    def enhance(
        self,
        analysis: SessionAIAnalysis,
        result: SessionResult,
        actions: list[RecordedAction],
        hints: list[ScenarioHintMessage],
    ) -> SessionAIAnalysis:
        root = str(self._repository_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        from ai.llm_report_enhancer import LLMReportEnhancer
        from ai.report_builder import SessionReportBuilder

        action_payloads = [
            item.model_dump(mode="json", by_alias=True) for item in actions
        ]
        report = SessionReportBuilder().build(
            session_id=str(result.session_id),
            result=result.model_dump(mode="json", by_alias=True),
            actions=action_payloads,
            issued_hints=[
                item.model_dump(mode="json", by_alias=True) for item in hints
            ],
        )
        enhanced = LLMReportEnhancer().enhance(report, actions=action_payloads)
        raw_provenance = enhanced.get("provenance", {})
        provenance_update = {
            "method": raw_provenance.get("method", "deterministic_template"),
            "llmAttempted": bool(raw_provenance.get("llmAttempted", False)),
            "llmUsed": bool(raw_provenance.get("llmUsed", False)),
            "llmStatus": raw_provenance.get("llmStatus"),
            "llmError": raw_provenance.get("llmError"),
            "llmErrorMessage": raw_provenance.get("llmErrorMessage"),
            "requestedModel": raw_provenance.get("requestedModel"),
            "resolvedModel": raw_provenance.get("resolvedModel"),
            "usage": raw_provenance.get("usage", {}),
            "scoreChanged": False,
            "sourceRefs": ["A-18", "учебное допущение"],
        }
        update: dict[str, object] = {
            "provenance": analysis.provenance.model_validate(provenance_update)
        }
        if raw_provenance.get("llmUsed") is True:
            update.update(
                {
                    "summary": enhanced["summary"],
                    "strengths": enhanced["strengths"],
                    "recommendations": enhanced["recommendations"],
                }
            )
        return analysis.model_copy(update=update)
