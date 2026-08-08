from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.domain import (
    CreateSessionRequest,
    ModelSnapshot,
    OperatorAction,
    SessionStatus,
    TrainingSession,
)
from app.scenarios import load_n1a_scenario
from app.simulation import (
    N1AProcessModel,
    SimulationCompletedError,
    StateVersionConflictError,
    load_n1a_model_profile,
)
from app.simulation.config import ModelProfile


class SessionNotFoundError(LookupError):
    pass


class InvalidSessionTransitionError(RuntimeError):
    pass


class SessionConflictError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionManager:
    """Owns one isolated deterministic model instance per training session."""

    def __init__(
        self,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._clock = clock
        self._id_factory = id_factory
        self._scenario = load_n1a_scenario()
        self._profile: ModelProfile = load_n1a_model_profile()
        self._sessions: dict[UUID, TrainingSession] = {}
        self._models: dict[UUID, N1AProcessModel] = {}
        self._processed_actions: dict[UUID, dict[str, UUID]] = {}
        self._lock = RLock()

    def create_session(self, request: CreateSessionRequest) -> TrainingSession:
        with self._lock:
            if request.scenario_id != self._scenario.scenario_id:
                raise SessionNotFoundError(
                    f"scenario '{request.scenario_id}' was not found"
                )

            session_id = self._id_factory()
            session = TrainingSession(
                session_id=session_id,
                scenario_id=self._scenario.scenario_id,
                scenario_version=self._scenario.scenario_version,
                trainee_id=request.trainee_id,
                instructor_id=request.instructor_id,
                mode=request.mode,
                status=SessionStatus.CREATED,
                created_at=self._clock(),
            )
            self._sessions[session_id] = session
            self._models[session_id] = self._new_model()
            self._processed_actions[session_id] = {}
            return session.model_copy(deep=True)

    def get_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            return self._require_session(session_id).model_copy(deep=True)

    def start_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.CREATED})
            snapshot = self._models[session_id].initialize(session_id)
            updated = session.model_copy(
                update={
                    "status": SessionStatus.RUNNING,
                    "started_at": self._clock(),
                    "virtual_time_ms": snapshot.virtual_time_ms,
                    "state_version": snapshot.state_version,
                }
            )
            self._sessions[session_id] = updated
            return updated.model_copy(deep=True)

    def pause_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.RUNNING})
            updated = session.model_copy(update={"status": SessionStatus.PAUSED})
            self._sessions[session_id] = updated
            return updated.model_copy(deep=True)

    def resume_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.PAUSED})
            updated = session.model_copy(update={"status": SessionStatus.RUNNING})
            self._sessions[session_id] = updated
            return updated.model_copy(deep=True)

    def complete_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(
                session_id,
                {SessionStatus.RUNNING, SessionStatus.PAUSED},
            )
            updated = session.model_copy(
                update={
                    "status": SessionStatus.COMPLETED,
                    "completed_at": self._clock(),
                }
            )
            self._sessions[session_id] = updated
            return updated.model_copy(deep=True)

    def advance_session(self, session_id: UUID, dt_ms: int) -> ModelSnapshot:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.RUNNING})
            try:
                snapshot = self._models[session_id].step(dt_ms)
            except SimulationCompletedError as error:
                raise InvalidSessionTransitionError(str(error)) from error
            self._sync_model_state(session, snapshot)
            return snapshot

    def apply_action(
        self,
        session_id: UUID,
        action: OperatorAction,
    ) -> ModelSnapshot:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.RUNNING})
            if action.session_id != session_id:
                raise SessionConflictError("path session ID does not match action")

            processed = self._processed_actions[session_id]
            previous_action_id = processed.get(action.idempotency_key)
            if previous_action_id is not None:
                if previous_action_id != action.action_id:
                    raise SessionConflictError(
                        "idempotency key was already used by another action"
                    )
                return self._models[session_id].get_snapshot()

            try:
                snapshot = self._models[session_id].apply_action(action)
            except StateVersionConflictError as error:
                raise SessionConflictError(str(error)) from error
            processed[action.idempotency_key] = action.action_id
            self._sync_model_state(session, snapshot)
            return snapshot

    def get_snapshot(self, session_id: UUID) -> ModelSnapshot:
        with self._lock:
            session = self._require_session(session_id)
            if session.status is SessionStatus.CREATED:
                raise InvalidSessionTransitionError(
                    "session must be started before requesting a snapshot"
                )
            return self._models[session_id].get_snapshot()

    def _new_model(self) -> N1AProcessModel:
        return N1AProcessModel(self._scenario, self._profile)

    def _sync_model_state(
        self,
        session: TrainingSession,
        snapshot: ModelSnapshot,
    ) -> None:
        self._sessions[session.session_id] = session.model_copy(
            update={
                "virtual_time_ms": snapshot.virtual_time_ms,
                "state_version": snapshot.state_version,
            }
        )

    def _require_session(self, session_id: UUID) -> TrainingSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise SessionNotFoundError(
                f"session '{session_id}' was not found"
            ) from error

    def _require_status(
        self,
        session_id: UUID,
        allowed: set[SessionStatus],
    ) -> TrainingSession:
        session = self._require_session(session_id)
        if session.status not in allowed:
            allowed_values = ", ".join(sorted(item.value for item in allowed))
            raise InvalidSessionTransitionError(
                f"session status '{session.status.value}' is not one of: "
                f"{allowed_values}"
            )
        return session
