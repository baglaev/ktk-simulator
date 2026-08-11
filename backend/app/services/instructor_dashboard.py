from __future__ import annotations

from app.config import Settings
from app.domain import (
    InstructorOverview,
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
        directory: dict[str, tuple[str, str]] = {
            self._settings.auth_user_login: (
                "Демо-обучаемый",
                "demo_directory",
            ),
            **{
                trainee.login: (trainee.full_name, "demo_directory")
                for trainee in DEMO_CORPORATE_TRAINEES
            },
        }
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
        items.sort(key=lambda item: (item.full_name.casefold(), item.login.casefold()))
        return InstructorTraineeList(items=items, total=len(items))

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
