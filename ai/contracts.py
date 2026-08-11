"""Transport-independent contracts used by the AI prototype.

The module intentionally has no imports from ``backend``.  It accepts plain
dictionaries shaped like the current WebSocket telemetry and action journal,
which allows the AI module to be developed and tested independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


JsonObject = Mapping[str, Any]


@dataclass(frozen=True)
class ParameterObservation:
    parameter_id: str
    value: float
    unit: str = "1"
    status: str = "success"

    @property
    def value_percent(self) -> float:
        """Compatibility accessor for old AI rules; check ``unit`` first."""

        return self.value

    @classmethod
    def from_payload(cls, payload: JsonObject) -> "ParameterObservation":
        parameter_id = str(payload.get("parameterId", payload.get("id", "")))
        raw_value = payload.get("valuePercent", payload.get("value", 0.0))
        return cls(
            parameter_id=parameter_id,
            value=float(raw_value),
            unit=str(payload.get("unit", "%" if "valuePercent" in payload else "1")),
            status=str(payload.get("status", "success")),
        )


@dataclass(frozen=True)
class ComponentObservation:
    component_id: str
    status: str = "success"
    operating_state: str | None = None
    parameters: tuple[ParameterObservation, ...] = ()
    state: JsonObject = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: JsonObject) -> "ComponentObservation":
        raw_parameters = payload.get("parameters", ())
        if isinstance(raw_parameters, Mapping):
            raw_parameters = [
                {"parameterId": key, "value": value, "unit": "1"}
                for key, value in raw_parameters.items()
            ]
        parameters = tuple(
            ParameterObservation.from_payload(item)
            for item in raw_parameters
            if isinstance(item, Mapping)
        )
        raw_state = payload.get("state", {})
        state = raw_state if isinstance(raw_state, Mapping) else {}
        operating_state = payload.get("operatingState", state.get("operatingState"))
        return cls(
            component_id=str(payload.get("componentId", payload.get("id", ""))),
            status=str(payload.get("status", "success")),
            operating_state=str(operating_state) if operating_state is not None else None,
            parameters=parameters,
            state=state,
        )


@dataclass(frozen=True)
class ActionObservation:
    action_type: str
    target_id: str | None = None
    parameters: JsonObject = field(default_factory=dict)
    virtual_time_ms: int | None = None

    @classmethod
    def from_payload(cls, payload: JsonObject) -> "ActionObservation":
        raw_parameters = payload.get("parameters", {})
        parameters = raw_parameters if isinstance(raw_parameters, Mapping) else {}
        raw_time = payload.get(
            "virtualTimeMs",
            payload.get("elapsedTimeMs", payload.get("elapsedMs")),
        )
        return cls(
            action_type=str(payload.get("actionType", "")),
            target_id=(
                str(payload["targetId"])
                if payload.get("targetId") is not None
                else None
            ),
            parameters=parameters,
            virtual_time_ms=int(raw_time) if raw_time is not None else None,
        )


@dataclass(frozen=True)
class HintContext:
    session_id: str
    mode: str
    virtual_time_ms: int
    components: tuple[ComponentObservation, ...]
    actions: tuple[ActionObservation, ...] = ()

    @classmethod
    def from_payload(
        cls,
        snapshot: JsonObject,
        actions: Sequence[JsonObject | ActionObservation] = (),
        *,
        mode: str | None = None,
    ) -> "HintContext":
        raw_timing = snapshot.get("timing", {})
        timing = raw_timing if isinstance(raw_timing, Mapping) else {}
        raw_time = snapshot.get(
            "virtualTimeMs",
            timing.get("elapsedMs", timing.get("virtualTimeMs", 0)),
        )
        raw_components = snapshot.get("components", ())
        parsed_actions = tuple(
            item
            if isinstance(item, ActionObservation)
            else ActionObservation.from_payload(item)
            for item in actions
        )
        return cls(
            session_id=str(snapshot.get("sessionId", "")),
            mode=str(mode or snapshot.get("mode", "training")),
            virtual_time_ms=int(raw_time),
            components=tuple(
                ComponentObservation.from_payload(item)
                for item in raw_components
                if isinstance(item, Mapping)
            ),
            actions=parsed_actions,
        )


@dataclass(frozen=True)
class HintEvidence:
    kind: str
    ref_id: str
    fact: str

    def to_payload(self) -> dict[str, str]:
        return {"kind": self.kind, "refId": self.ref_id, "fact": self.fact}


@dataclass(frozen=True)
class Hint:
    hint_id: str
    level: str
    title: str
    message: str
    evidence: tuple[HintEvidence, ...]
    source_refs: tuple[str, ...]

    def to_payload(self, context: HintContext) -> dict[str, Any]:
        return {
            "type": "ai.hint",
            "sessionId": context.session_id,
            "virtualTimeMs": context.virtual_time_ms,
            "hintId": self.hint_id,
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "evidence": [item.to_payload() for item in self.evidence],
            "provenance": {
                "method": "deterministic_rule",
                "llmUsed": False,
                "sourceRefs": list(self.source_refs),
            },
        }
