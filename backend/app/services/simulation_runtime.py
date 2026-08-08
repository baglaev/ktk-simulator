from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.services.session_manager import (
    InvalidSessionTransitionError,
    SessionManager,
)


logger = logging.getLogger(__name__)


class SimulationRuntime:
    """Advance every running training session on one application clock."""

    def __init__(
        self,
        manager: SessionManager,
        tick_interval_ms: int,
        step_ms: int,
    ) -> None:
        if tick_interval_ms <= 0:
            raise ValueError("tickIntervalMs must be greater than zero")
        if step_ms <= 0:
            raise ValueError("stepMs must be greater than zero")
        self._manager = manager
        self._tick_interval_seconds = tick_interval_ms / 1_000
        self._step_ms = step_ms
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        self._task = asyncio.create_task(
            self._run(),
            name="simulation-runtime",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def tick_once(self) -> None:
        """Perform one deterministic step for each currently running session."""

        for session_id in self._manager.running_session_ids():
            self._advance_session(session_id)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._tick_interval_seconds)
            self.tick_once()

    def _advance_session(self, session_id: UUID) -> None:
        try:
            self._manager.advance_session(session_id, self._step_ms)
        except InvalidSessionTransitionError:
            # A lifecycle request may pause or complete a session between the
            # selection of running IDs and its step. The next tick will use the
            # new status.
            return
        except Exception:
            logger.exception(
                "Failed to advance simulation session %s",
                session_id,
            )
