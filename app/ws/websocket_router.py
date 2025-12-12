from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, Query, status

from .connection import ConnectionManager
from utils.auth import verify_token

router = APIRouter()
manager = ConnectionManager()

@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, token: Annotated[str, Query()] = None):
    if token is None or not verify_token(token):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
