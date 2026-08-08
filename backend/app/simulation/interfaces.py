from typing import Protocol
from uuid import UUID

from app.domain import ModelSnapshot, OperatorAction


class ProcessModel(Protocol):
    def initialize(self, session_id: UUID) -> ModelSnapshot: ...

    def step(self, dt_ms: int) -> ModelSnapshot: ...

    def apply_action(self, action: OperatorAction) -> ModelSnapshot: ...

    def get_snapshot(self) -> ModelSnapshot: ...
