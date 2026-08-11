from __future__ import annotations

from app.config import Settings
from app.domain import (
    InstructorJournalItem,
    InstructorOverview,
    InstructorResultItem,
    InstructorResultsCollection,
    InstructorTrainee,
    InstructorTraineeList,
)
from app.services.demo_corporate_accounts import DEMO_CORPORATE_TRAINEES
from app.services.session_manager import SessionManager


class InstructorDashboardService:
    """Build instructor views without exposing demo account passwords."""

    def __init__(self, manager: SessionManager, settings: Settings) -> None:
        self._manager = manager
        self._settings = settings

    def list_trainees(self) -> InstructorTraineeList:
        statistics = self._manager.list_trainee_result_statistics()
        directory = self._trainee_directory()
        for trainee_id in statistics:
            directory.setdefault(
                trainee_id,
                (trainee_id, "session_history"),
            )

        items = []
        for trainee_id, (full_name, source) in directory.items():
            aggregate = statistics.get(trainee_id)
            items.append(
                InstructorTrainee(
                    trainee_id=trainee_id,
                    login=trainee_id,
                    full_name=full_name,
                    assigned_instructor_id=self._settings.auth_instructor_login,
                    account_source=source,
                    attempts_count=(aggregate.attempts_count if aggregate else 0),
                    successful_attempts_count=(
                        aggregate.successful_attempts_count if aggregate else 0
                    ),
                    average_score=(aggregate.average_score if aggregate else None),
                    best_score=(aggregate.best_score if aggregate else None),
                    last_completed_at=(
                        aggregate.last_completed_at if aggregate else None
                    ),
                    latest_result=(aggregate.latest_result if aggregate else None),
                )
            )
        items.sort(
            key=lambda item: (
                item.full_name.casefold(),
                item.login.casefold(),
            )
        )
        return InstructorTraineeList(items=items, total=len(items))

    def list_results(self) -> InstructorResultsCollection:
        """Return every result with trainee name and its complete journal."""

        results = self._manager.list_all_trainee_results()
        directory = self._trainee_directory()
        items = []
        for result in results.items:
            journal = [
                InstructorJournalItem(
                    time=_format_virtual_time(action.virtual_time_ms),
                    virtual_time_ms=action.virtual_time_ms,
                    kind="action",
                    description=action.description,
                )
                for action in self._manager.list_actions(result.session_id)
            ]
            journal.extend(
                InstructorJournalItem(
                    time=_format_virtual_time(hint.virtual_time_ms),
                    virtual_time_ms=hint.virtual_time_ms,
                    kind="hint",
                    description=f"ИИ-подсказка: {hint.title}. {hint.message}",
                )
                for hint in self._manager.list_hints(result.session_id)
            )
            journal.sort(key=lambda item: (item.virtual_time_ms, item.kind))
            trainee_name = directory.get(
                result.trainee_id,
                (result.trainee_id, "session_history"),
            )[0]
            items.append(
                InstructorResultItem(
                    **result.model_dump(),
                    trainee_name=trainee_name,
                    journal=journal,
                )
            )
        return InstructorResultsCollection(items=items, total=results.total)

    def _trainee_directory(self) -> dict[str, tuple[str, str]]:
        return {
            self._settings.auth_user_login: (
                "Демо-обучаемый",
                "demo_directory",
            ),
            **{
                trainee.login: (trainee.full_name, "demo_directory")
                for trainee in DEMO_CORPORATE_TRAINEES
            },
        }

    def get_trainee(self, trainee_id: str) -> InstructorTrainee | None:
        return next(
            (
                item
                for item in self.list_trainees().items
                if item.trainee_id == trainee_id
            ),
            None,
        )

    def get_overview(self) -> InstructorOverview:
        trainees = self.list_trainees().items
        completed_attempts = sum(item.attempts_count for item in trainees)
        successful_attempts = sum(
            item.successful_attempts_count for item in trainees
        )
        weighted_score = sum(
            (item.average_score or 0) * item.attempts_count
            for item in trainees
        )
        return InstructorOverview(
            total_trainees=len(trainees),
            trainees_with_attempts=sum(
                item.attempts_count > 0 for item in trainees
            ),
            completed_attempts=completed_attempts,
            successful_attempts=successful_attempts,
            average_score=(
                round(weighted_score / completed_attempts)
                if completed_attempts
                else None
            ),
        )


def _format_virtual_time(value_ms: int) -> str:
    minutes, seconds = divmod(value_ms // 1_000, 60)
    return f"{minutes:02d}:{seconds:02d}"
