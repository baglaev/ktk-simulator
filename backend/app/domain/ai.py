from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, JsonValue

from app.domain.base import APIModel
from app.domain.enums import GeneralStatus, ResultStatus, TrainingMode


class AIErrorCard(APIModel):
    order: int = Field(ge=1)
    code: str = Field(min_length=1)
    classification: Literal[
        "diagnostics",
        "sequence",
        "safety",
        "monitoring",
        "timeliness",
    ]
    status: GeneralStatus
    detected_at_ms: int = Field(ge=0)
    user_action: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    correct_approach: str = Field(min_length=1)
    prediction: str = Field(min_length=1)
    hint_shown_at_ms: int | None = Field(default=None, ge=0)


class AIAnalysisProvenance(APIModel):
    method: Literal[
        "deterministic_template",
        "deterministic_plus_llm",
    ] = "deterministic_template"
    llm_attempted: bool = False
    llm_used: bool = False
    llm_status: str | None = None
    llm_error: str | None = None
    llm_error_message: str | None = None
    requested_model: str | None = None
    resolved_model: str | None = None
    usage: dict[str, JsonValue] = Field(default_factory=dict)
    score_changed: Literal[False] = False
    source_refs: list[str] = Field(default_factory=list)


class SessionAIAnalysis(APIModel):
    type: Literal["ai.session_analysis"] = "ai.session_analysis"
    session_id: UUID
    result_status: ResultStatus
    total_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    errors: list[AIErrorCard] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    provenance: AIAnalysisProvenance


class AdaptivePlanItem(APIModel):
    priority: int = Field(ge=1)
    skill: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    next_mode: TrainingMode
    success_criterion: str = Field(min_length=1)


class AdaptiveRepetitionPlan(APIModel):
    type: Literal["ai.adaptive_plan"] = "ai.adaptive_plan"
    session_id: UUID
    items: list[AdaptivePlanItem] = Field(default_factory=list)
    summary: str = Field(min_length=1)


class AssistantQuestionRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
