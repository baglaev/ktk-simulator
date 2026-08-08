from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from app.domain.enums import ParameterOrigin


def to_camel(value: str) -> str:
    """Convert a snake_case field name to the frontend camelCase format."""

    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class APIModel(BaseModel):
    """Base class for strict versioned API contracts."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class Provenance(APIModel):
    """Traceability marker for a parameter used by the training model."""

    origin: ParameterOrigin
    source_ref_id: str | None = None
    assumption_id: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> Provenance:
        if self.origin is ParameterOrigin.SOURCE and not self.source_ref_id:
            raise ValueError("sourceRefId is required when origin is 'source'")
        if (
            self.origin is ParameterOrigin.EDUCATIONAL_ASSUMPTION
            and not self.assumption_id
        ):
            raise ValueError(
                "assumptionId is required when origin is 'educational_assumption'"
            )
        return self
