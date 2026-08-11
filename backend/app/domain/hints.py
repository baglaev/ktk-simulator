from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.domain.base import APIModel
from app.domain.enums import GeneralStatus


class HintEvidence(APIModel):
    kind: Literal["component", "signal", "action"]
    ref_id: str = Field(min_length=1)
    fact: str = Field(min_length=1)


class HintProvenance(APIModel):
    method: Literal["deterministic_rule"] = "deterministic_rule"
    llm_used: Literal[False] = False
    source_refs: list[str] = Field(default_factory=list)


class ScenarioHintMessage(APIModel):
    """Prepared live hint sent only in training mode over WebSocket."""

    type: Literal["scenario.hint"] = "scenario.hint"
    session_id: UUID
    virtual_time_ms: int = Field(ge=0)
    hint_id: str = Field(min_length=1)
    level: GeneralStatus
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    display_duration_ms: int = Field(default=8_000, ge=1_000, le=30_000)
    evidence: list[HintEvidence] = Field(default_factory=list)
    provenance: HintProvenance
