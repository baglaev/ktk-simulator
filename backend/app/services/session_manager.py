from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.domain import (
    CreateSessionRequest,
    ModelSnapshot,
    OperatorAction,
    RecordedAction,
    SessionResult,
    SessionStatus,
    TrainingSession,
)
from app.evaluation import evaluate_session
from app.persistence import SessionRepository, create_database
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
        snapshot_publisher: Callable[[UUID, ModelSnapshot], None] | None = None,
        repository: SessionRepository | None = None,
    ) -> None:
        self._clock = clock
        self._id_factory = id_factory
        self._scenario = load_n1a_scenario()
        self._profile: ModelProfile = load_n1a_model_profile()
        self._snapshot_publisher = snapshot_publisher or (
            lambda _id, _snapshot: None
        )
        if repository is None:
            _, session_factory = create_database("sqlite+pysqlite:///:memory:")
            repository = SessionRepository(session_factory)
        self._repository = repository
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
                model_id=self._profile.model_id,
                model_version=self._profile.model_version,
                trainee_id=request.trainee_id,
                instructor_id=request.instructor_id,
                mode=request.mode,
                status=SessionStatus.CREATED,
                total_duration_ms=self._profile.total_duration_ms,
                created_at=self._clock(),
            )
            self._sessions[session_id] = session
            self._models[session_id] = self._new_model()
            self._processed_actions[session_id] = {}
            self._repository.save_session(session)
            return session.model_copy(deep=True)

    def get_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            return self._require_session(session_id).model_copy(deep=True)

    def running_session_ids(self) -> tuple[UUID, ...]:
        with self._lock:
            return tuple(
                session_id
                for session_id, session in self._sessions.items()
                if session.status is SessionStatus.RUNNING
            )

    def start_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.CREATED})
            snapshot = self._models[session_id].initialize(session_id)
            updated = session.model_copy(
                update={
                    "status": SessionStatus.RUNNING,
                    "started_at": self._clock(),
                    "elapsed_time_ms": snapshot.timing.elapsed_ms,
                    "state_version": snapshot.state_version,
                }
            )
            self._sessions[session_id] = updated
            self._repository.save_session(updated)
            self._snapshot_publisher(session_id, snapshot)
            return updated.model_copy(deep=True)

    def pause_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.RUNNING})
            updated = session.model_copy(update={"status": SessionStatus.PAUSED})
            self._sessions[session_id] = updated
            self._repository.save_session(updated)
            return updated.model_copy(deep=True)

    def resume_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.PAUSED})
            updated = session.model_copy(update={"status": SessionStatus.RUNNING})
            self._sessions[session_id] = updated
            self._repository.save_session(updated)
            return updated.model_copy(deep=True)

    def complete_session(self, session_id: UUID) -> TrainingSession:
        with self._lock:
            session = self._require_status(
                session_id,
                {
                    SessionStatus.RUNNING,
                    SessionStatus.PAUSED,
                    SessionStatus.READY_TO_COMPLETE,
                },
            )
            model = self._models[session_id]
            completed_at = self._clock()
            result = evaluate_session(
                session_id=session_id,
                actions=model.get_recorded_actions(),
                completed_at=completed_at,
                safe_configuration=model.has_safe_configuration(),
                stabilized=model.is_stabilized,
                min_lrca_605=model.min_lrca_605,
                model_failure_reason=model.failure_reason,
            )
            updated = session.model_copy(
                update={
                    "status": (
                        SessionStatus.COMPLETED
                        if result.outcome.value == "success"
                        else SessionStatus.FAILED
                    ),
                    "completed_at": completed_at,
                }
            )
            self._sessions[session_id] = updated
            self._repository.save_session(updated)
            self._repository.save_result(result)
            return updated.model_copy(deep=True)

    def advance_session(self, session_id: UUID, dt_ms: int) -> ModelSnapshot:
        with self._lock:
            session = self._require_status(session_id, {SessionStatus.RUNNING})
            try:
                snapshot = self._models[session_id].step(dt_ms)
            except SimulationCompletedError as error:
                raise InvalidSessionTransitionError(str(error)) from error
            self._sync_model_state(session, snapshot)
            self._snapshot_publisher(session_id, snapshot)
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
            except ValueError as error:
                raise SessionConflictError(str(error)) from error
            processed[action.idempotency_key] = action.action_id
            recorded_action = self._models[session_id].get_recorded_actions()[-1]
            self._repository.save_action(recorded_action)
            self._sync_model_state(session, snapshot)
            self._snapshot_publisher(session_id, snapshot)
            return snapshot

    def get_snapshot(self, session_id: UUID) -> ModelSnapshot:
        with self._lock:
            session = self._require_session(session_id)
            if session.status is SessionStatus.CREATED:
                raise InvalidSessionTransitionError(
                    "session must be started before requesting a snapshot"
                )
            model = self._models.get(session_id)
            if model is None:
                raise InvalidSessionTransitionError(
                    "live model state is unavailable after backend restart; "
                    "the persisted session audit and result remain available"
                )
            return model.get_snapshot()

    def list_actions(self, session_id: UUID) -> list[RecordedAction]:
        with self._lock:
            self._require_session(session_id)
            return self._repository.list_actions(session_id)

    def get_result(self, session_id: UUID) -> SessionResult:
        with self._lock:
            self._require_session(session_id)
            result = self._repository.get_result(session_id)
            if result is None:
                raise InvalidSessionTransitionError(
                    "session result is available after completion"
                )
            return result

    def _new_model(self) -> N1AProcessModel:
        return N1AProcessModel(self._scenario, self._profile)

    def _sync_model_state(
        self,
        session: TrainingSession,
        snapshot: ModelSnapshot,
    ) -> None:
        update: dict[str, object] = {
            "elapsed_time_ms": snapshot.timing.elapsed_ms,
            "state_version": snapshot.state_version,
        }
        model = self._models[session.session_id]
        if model.is_stabilized:
            update["status"] = SessionStatus.READY_TO_COMPLETE
        elif model.is_failed:
            completed_at = self._clock()
            update.update(
                {
                    "status": SessionStatus.FAILED,
                    "completed_at": completed_at,
                }
            )
            result = evaluate_session(
                session_id=session.session_id,
                actions=model.get_recorded_actions(),
                completed_at=completed_at,
                safe_configuration=model.has_safe_configuration(),
                stabilized=model.is_stabilized,
                min_lrca_605=model.min_lrca_605,
                model_failure_reason=model.failure_reason,
            )
            self._repository.save_result(result)
        updated = session.model_copy(update=update)
        self._sessions[session.session_id] = updated
        self._repository.save_session(updated)

    def _require_session(self, session_id: UUID) -> TrainingSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            persisted = self._repository.get_session(session_id)
            if persisted is not None:
                self._sessions[session_id] = persisted
                return persisted
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
