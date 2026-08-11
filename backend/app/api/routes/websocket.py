from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.dependencies import get_session_broker, get_session_manager
from app.domain import (
    APIModel,
    ActionAcceptedMessage,
    ActionErrorDetail,
    ActionRejectedMessage,
    ModelSnapshot,
    ScenarioActionRequest,
)
from app.realtime import SessionSnapshotBroker, build_telemetry_update
from app.services import (
    InvalidSessionTransitionError,
    SessionConflictError,
    SessionManager,
    SessionNotFoundError,
)


router = APIRouter(tags=["telemetry"])


@router.websocket("/ws/v1/sessions/{session_id}")
async def stream_session_telemetry(
    websocket: WebSocket,
    session_id: UUID,
    manager: SessionManager = Depends(get_session_manager),
    broker: SessionSnapshotBroker = Depends(get_session_broker),
) -> None:
    """Exchange minimal user actions and ordered live telemetry updates."""

    origin = websocket.headers.get("origin")
    allowed_origins = websocket.app.state.settings.cors_allowed_origins
    if origin and "*" not in allowed_origins and origin not in allowed_origins:
        await websocket.close(code=4403, reason="Origin is not allowed")
        return

    queue = broker.subscribe(session_id)
    try:
        try:
            previous = manager.get_snapshot(session_id)
        except SessionNotFoundError:
            await websocket.close(code=4404, reason="Session not found")
            return
        except InvalidSessionTransitionError:
            await websocket.close(code=4409, reason="Session is not started")
            return

        await websocket.accept()
        await websocket.send_json(
            previous.model_dump(mode="json", by_alias=True)
        )
        send_lock = anyio.Lock()

        async def send_message(message: APIModel) -> None:
            async with send_lock:
                await websocket.send_json(
                    message.model_dump(mode="json", by_alias=True)
                )

        async def send_updates() -> None:
            nonlocal previous
            while True:
                current = await queue.get()
                if not isinstance(current, ModelSnapshot):
                    await send_message(current)
                    continue
                if current.sequence_no <= previous.sequence_no:
                    continue

                update = build_telemetry_update(previous, current)
                previous = current
                if update is not None:
                    await send_message(update)

        async def receive_actions(
            task_group: anyio.abc.TaskGroup,
        ) -> None:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    task_group.cancel_scope.cancel()
                    return

                payload = message.get("text")
                if payload is None:
                    await send_message(
                        _rejected(
                            "invalid_message",
                            "Action must be sent as a JSON text message",
                        )
                    )
                    continue

                try:
                    request = ScenarioActionRequest.model_validate_json(payload)
                except ValidationError:
                    await send_message(
                        _rejected(
                            "invalid_action",
                            "Action must contain a valid actionType, targetId "
                            "and optional parameters",
                        )
                    )
                    continue

                try:
                    # Keep the acknowledgement ahead of the telemetry update
                    # already queued by SessionManager.apply_scenario_action.
                    async with send_lock:
                        action_id, snapshot = manager.apply_scenario_action(
                            session_id,
                            request,
                        )
                        accepted = ActionAcceptedMessage(
                            action_id=action_id,
                            state_version=snapshot.state_version,
                        )
                        await websocket.send_json(
                            accepted.model_dump(mode="json", by_alias=True)
                        )
                except SessionNotFoundError as error:
                    await send_message(_rejected("session_not_found", str(error)))
                except InvalidSessionTransitionError as error:
                    await send_message(
                        _rejected("session_not_running", str(error))
                    )
                except SessionConflictError as error:
                    await send_message(_rejected("action_rejected", str(error)))

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(send_updates)
            task_group.start_soon(receive_actions, task_group)
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(session_id, queue)


def _rejected(code: str, message: str) -> ActionRejectedMessage:
    return ActionRejectedMessage(
        error=ActionErrorDetail(code=code, message=message),
    )
