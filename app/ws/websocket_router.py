import json
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    Depends,
    status,
)
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from sqlmodel import Session, select

import services.messaging as messaging_service
from .connection import manager
from db.session import get_session
from schemas.ws import WSRequest, WSMessageCreate, WSMessageEdit, WSMessageDelete
from utils.auth import get_token_user_id_ws

router = APIRouter(prefix='/ws')

EVENT_HANDLERS = {
    'message.create': (WSMessageCreate, messaging_service.create_message, 'conversation.{conversation_id}.created'),
    'message.edit': (WSMessageEdit, messaging_service.edit_message, 'conversation.{conversation_id}.edited'),
    'message.delete': (WSMessageDelete, messaging_service.delete_message, 'conversation.{conversation_id}.deleted'),
}

@router.websocket('')
async def ws_messages_endpoint(
    websocket: WebSocket,
    user_id: Annotated[uuid.UUID, Depends(get_token_user_id_ws)],
    session: Session = Depends(get_session)
):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            ws_request = WSRequest.model_validate(data)

            if ws_request.type not in EVENT_HANDLERS:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            payload_schema, handler, routing_key_template = EVENT_HANDLERS[ws_request.type]

            payload = payload_schema.model_validate(ws_request.payload).model_dump()

            try:
                result = await run_in_threadpool(handler, session, user_id, payload)
            except messaging_service.PermissionError:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            except ValueError:
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                return
            
            event = {
                'type': ws_request.type,
                'payload': result,
            }

            await websocket.app.state.message_publisher.publish(
                routing_key=routing_key_template.format(**result),
                payload=event,
            )
    except ValidationError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        pass
    except json.JSONDecodeError:
        raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA)
    finally:
        manager.disconnect(user_id)
