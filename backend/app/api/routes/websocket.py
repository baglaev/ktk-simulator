from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.dependencies import get_session_broker, get_session_manager
from app.realtime import SessionSnapshotBroker, build_telemetry_delta
from app.services import (
    InvalidSessionTransitionError,
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
    """Send one full snapshot followed by ordered telemetry deltas."""

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

        async def send_updates() -> None:
            nonlocal previous
            while True:
                current = await queue.get()
                if current.sequence_no <= previous.sequence_no:
                    continue

                delta = build_telemetry_delta(previous, current)
                previous = current
                if delta is not None:
                    await websocket.send_json(
                        delta.model_dump(mode="json", by_alias=True)
                    )

        async def wait_for_disconnect(
            task_group: anyio.abc.TaskGroup,
        ) -> None:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    task_group.cancel_scope.cancel()
                    return

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(send_updates)
            task_group.start_soon(wait_for_disconnect, task_group)
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(session_id, queue)
