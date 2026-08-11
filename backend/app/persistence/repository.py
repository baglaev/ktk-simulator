from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain import (
    RecordedAction,
    ScenarioHintMessage,
    SessionResult,
    TraineeResultSummary,
    TrainingMode,
    TrainingSession,
)
from app.persistence.models import (
    AppUserRecord,
    OperatorActionRecord,
    IssuedHintRecord,
    SessionAIAnalysisRecord,
    SessionResultRecord,
    TrainingSessionRecord,
)


@dataclass(frozen=True)
class TraineeResultStatistics:
    attempts_count: int
    successful_attempts_count: int
    average_score: int
    best_score: int
    last_completed_at: datetime
    latest_result: TraineeResultSummary


@dataclass(frozen=True)
class StoredUserAccount:
    login: str
    password_hash: str
    role: str
    full_name: str
    assigned_instructor_id: str | None
    is_active: bool


@dataclass(frozen=True)
class UserDirectoryEntry:
    login: str
    full_name: str
    assigned_instructor_id: str | None


class SessionRepository:
    """Synchronous audit repository used inside the manager's process lock."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_user_account(self, login: str) -> StoredUserAccount | None:
        with self._session_factory() as database:
            item = database.get(AppUserRecord, login)
            if item is None:
                return None
            return StoredUserAccount(
                login=item.login,
                password_hash=item.password_hash,
                role=item.role,
                full_name=item.full_name,
                assigned_instructor_id=item.assigned_instructor_id,
                is_active=item.is_active,
            )

    def list_user_directory(self, role: str) -> list[UserDirectoryEntry]:
        with self._session_factory() as database:
            records = database.scalars(
                select(AppUserRecord)
                .where(
                    AppUserRecord.role == role,
                    AppUserRecord.is_active.is_(True),
                )
                .order_by(AppUserRecord.full_name, AppUserRecord.login)
            ).all()
        return [
            UserDirectoryEntry(
                login=item.login,
                full_name=item.full_name,
                assigned_instructor_id=item.assigned_instructor_id,
            )
            for item in records
        ]

    def save_user_account(
        self,
        *,
        login: str,
        password_hash: str,
        role: str,
        full_name: str,
        assigned_instructor_id: str | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
    ) -> None:
        record = AppUserRecord(
            login=login,
            password_hash=password_hash,
            role=role,
            full_name=full_name,
            assigned_instructor_id=assigned_instructor_id,
            is_active=is_active,
            created_at=created_at or datetime.now(timezone.utc),
        )
        with self._session_factory.begin() as database:
            database.merge(record)

    def save_session(self, item: TrainingSession) -> None:
        payload = item.model_dump(mode="python")
        record = TrainingSessionRecord(
            session_id=str(item.session_id),
            scenario_id=item.scenario_id,
            scenario_version=item.scenario_version,
            model_id=item.model_id,
            model_version=item.model_version,
            trainee_id=item.trainee_id,
            instructor_id=item.instructor_id,
            mode=item.mode.value,
            status=item.status.value,
            elapsed_time_ms=item.elapsed_time_ms,
            total_duration_ms=item.total_duration_ms,
            state_version=item.state_version,
            created_at=payload["created_at"],
            started_at=payload["started_at"],
            completed_at=payload["completed_at"],
        )
        with self._session_factory.begin() as database:
            database.merge(record)

    def get_session(self, session_id) -> TrainingSession | None:
        with self._session_factory() as database:
            item = database.get(TrainingSessionRecord, str(session_id))
            if item is None:
                return None
            return TrainingSession.model_validate(
                {
                    "sessionId": item.session_id,
                    "scenarioId": item.scenario_id,
                    "scenarioVersion": item.scenario_version,
                    "modelId": item.model_id,
                    "modelVersion": item.model_version,
                    "traineeId": item.trainee_id,
                    "instructorId": item.instructor_id,
                    "mode": item.mode,
                    "status": item.status,
                    "elapsedTimeMs": item.elapsed_time_ms,
                    "totalDurationMs": item.total_duration_ms,
                    "stateVersion": item.state_version,
                    "createdAt": _aware(item.created_at),
                    "startedAt": _aware(item.started_at),
                    "completedAt": _aware(item.completed_at),
                }
            )

    def save_action(self, item: RecordedAction) -> None:
        record = OperatorActionRecord(
            action_id=str(item.action_id),
            session_id=str(item.session_id),
            sequence_no=item.sequence_no,
            virtual_time_ms=item.virtual_time_ms,
            action_type=item.action_type.value,
            target_id=item.target_id,
            parameters_json=item.parameters,
            description=item.description,
            error_codes_json=[code.value for code in item.error_codes],
            submitted_at=item.submitted_at,
        )
        with self._session_factory.begin() as database:
            database.merge(record)

    def list_actions(self, session_id) -> list[RecordedAction]:
        with self._session_factory() as database:
            records = database.scalars(
                select(OperatorActionRecord)
                .where(OperatorActionRecord.session_id == str(session_id))
                .order_by(OperatorActionRecord.sequence_no)
            ).all()
        return [
            RecordedAction.model_validate(
                {
                    "actionId": item.action_id,
                    "sessionId": item.session_id,
                    "sequenceNo": item.sequence_no,
                    "virtualTimeMs": item.virtual_time_ms,
                    "actionType": item.action_type,
                    "targetId": item.target_id,
                    "parameters": item.parameters_json,
                    "description": item.description,
                    "errorCodes": item.error_codes_json,
                    "submittedAt": _aware(item.submitted_at),
                }
            )
            for item in records
        ]

    def save_result(self, item: SessionResult) -> None:
        record = SessionResultRecord(
            session_id=str(item.session_id),
            outcome=item.outcome.value,
            total_score=item.total_score,
            payload_json=item.model_dump(mode="json", by_alias=True),
            completed_at=item.completed_at,
        )
        with self._session_factory.begin() as database:
            database.merge(record)

    def get_result(self, session_id) -> SessionResult | None:
        with self._session_factory() as database:
            record = database.get(SessionResultRecord, str(session_id))
            if record is None:
                return None
            return SessionResult.model_validate(record.payload_json)

    def list_result_summaries(
        self,
        *,
        trainee_id: str | None = None,
        instructor_id: str | None = None,
        mode: TrainingMode | None = None,
        limit: int | None = 100,
        offset: int = 0,
    ) -> tuple[list[TraineeResultSummary], int]:
        """Return completed attempts ordered from newest to oldest."""

        filters = []
        if trainee_id is not None:
            filters.append(TrainingSessionRecord.trainee_id == trainee_id)
        if instructor_id is not None:
            filters.append(TrainingSessionRecord.instructor_id == instructor_id)
        if mode is not None:
            filters.append(TrainingSessionRecord.mode == mode.value)

        joined = (
            select(TrainingSessionRecord, SessionResultRecord)
            .join(
                SessionResultRecord,
                SessionResultRecord.session_id
                == TrainingSessionRecord.session_id,
            )
            .where(*filters)
        )
        count_query = (
            select(func.count())
            .select_from(TrainingSessionRecord)
            .join(
                SessionResultRecord,
                SessionResultRecord.session_id
                == TrainingSessionRecord.session_id,
            )
            .where(*filters)
        )

        with self._session_factory() as database:
            total = int(database.scalar(count_query) or 0)
            result_query = joined.order_by(
                SessionResultRecord.completed_at.desc()
            )
            if limit is not None:
                result_query = result_query.limit(limit).offset(offset)
            records = database.execute(result_query).all()

        items: list[TraineeResultSummary] = []
        for session_record, result_record in records:
            result = SessionResult.model_validate(result_record.payload_json)
            items.append(
                TraineeResultSummary(
                    session_id=session_record.session_id,
                    trainee_id=session_record.trainee_id,
                    instructor_id=session_record.instructor_id,
                    scenario_id=session_record.scenario_id,
                    scenario_version=session_record.scenario_version,
                    mode=session_record.mode,
                    session_status=session_record.status,
                    result_status=result.status,
                    outcome=result.outcome,
                    total_score=result.total_score,
                    max_score=result.max_score,
                    elapsed_time_ms=result.elapsed_time_ms,
                    completed_at=_aware(result_record.completed_at),
                )
            )
        return items, total

    def list_trainee_result_statistics(
        self,
    ) -> dict[str, TraineeResultStatistics]:
        """Aggregate all persisted terminal attempts by trainee identifier."""

        query = (
            select(
                TrainingSessionRecord.trainee_id,
                func.count(SessionResultRecord.session_id),
                func.sum(
                    case(
                        (SessionResultRecord.outcome == "success", 1),
                        else_=0,
                    )
                ),
                func.avg(SessionResultRecord.total_score),
                func.max(SessionResultRecord.total_score),
                func.max(SessionResultRecord.completed_at),
            )
            .join(
                SessionResultRecord,
                SessionResultRecord.session_id
                == TrainingSessionRecord.session_id,
            )
            .group_by(TrainingSessionRecord.trainee_id)
        )
        with self._session_factory() as database:
            records = database.execute(query).all()

            latest_records = database.execute(
                select(TrainingSessionRecord, SessionResultRecord)
                .join(
                    SessionResultRecord,
                    SessionResultRecord.session_id
                    == TrainingSessionRecord.session_id,
                )
                .order_by(SessionResultRecord.completed_at.desc())
            ).all()

        latest_results: dict[str, TraineeResultSummary] = {}
        for session_record, result_record in latest_records:
            if session_record.trainee_id in latest_results:
                continue
            result = SessionResult.model_validate(result_record.payload_json)
            latest_results[session_record.trainee_id] = TraineeResultSummary(
                session_id=session_record.session_id,
                trainee_id=session_record.trainee_id,
                instructor_id=session_record.instructor_id,
                scenario_id=session_record.scenario_id,
                scenario_version=session_record.scenario_version,
                mode=session_record.mode,
                session_status=session_record.status,
                result_status=result.status,
                outcome=result.outcome,
                total_score=result.total_score,
                max_score=result.max_score,
                elapsed_time_ms=result.elapsed_time_ms,
                completed_at=_aware(result_record.completed_at),
            )

        return {
            trainee_id: TraineeResultStatistics(
                attempts_count=int(attempts_count),
                successful_attempts_count=int(successful_attempts_count or 0),
                average_score=round(float(average_score)),
                best_score=int(best_score),
                last_completed_at=_aware(last_completed_at),
                latest_result=latest_results[trainee_id],
            )
            for (
                trainee_id,
                attempts_count,
                successful_attempts_count,
                average_score,
                best_score,
                last_completed_at,
            ) in records
        }

    def save_hint(self, item: ScenarioHintMessage) -> None:
        record = IssuedHintRecord(
            hint_record_id=f"{item.session_id}:{item.hint_id}",
            session_id=str(item.session_id),
            hint_id=item.hint_id,
            virtual_time_ms=item.virtual_time_ms,
            payload_json=item.model_dump(mode="json", by_alias=True),
        )
        with self._session_factory.begin() as database:
            database.merge(record)

    def list_hints(self, session_id) -> list[ScenarioHintMessage]:
        with self._session_factory() as database:
            records = database.scalars(
                select(IssuedHintRecord)
                .where(IssuedHintRecord.session_id == str(session_id))
                .order_by(IssuedHintRecord.virtual_time_ms, IssuedHintRecord.hint_id)
            ).all()
        return [
            ScenarioHintMessage.model_validate(
                _adopt_legacy_hint_payload(item.payload_json)
            )
            for item in records
        ]

    def save_ai_analysis(
        self,
        session_id,
        payload: dict,
        created_at: datetime,
    ) -> None:
        record = SessionAIAnalysisRecord(
            session_id=str(session_id),
            payload_json=payload,
            created_at=created_at,
        )
        with self._session_factory.begin() as database:
            database.merge(record)

    def get_ai_analysis(self, session_id) -> dict | None:
        with self._session_factory() as database:
            record = database.get(SessionAIAnalysisRecord, str(session_id))
            return None if record is None else dict(record.payload_json)


def _adopt_legacy_hint_payload(value: dict) -> dict:
    """Remove the retired storage-only mode field from archived hints."""

    payload = dict(value)
    payload.pop("mode", None)
    return payload


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
