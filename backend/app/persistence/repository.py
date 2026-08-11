from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain import RecordedAction, ScenarioHintMessage, SessionResult, TrainingSession
from app.persistence.models import (
    OperatorActionRecord,
    IssuedHintRecord,
    SessionAIAnalysisRecord,
    SessionResultRecord,
    TrainingSessionRecord,
)


class SessionRepository:
    """Synchronous audit repository used inside the manager's process lock."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
            ScenarioHintMessage.model_validate(item.payload_json)
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


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
