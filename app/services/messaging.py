import json
import logging

import aio_pika
from sqlmodel import Session, select

from db.session import get_session
from schemas import ConversationParticipant, Message
from ws.connection import manager

logger = logging.getLogger(__name__)

async def rmq_websocket_handler(inc_message: aio_pika.IncomingMessage) -> None:
    try:
        data = json.loads(inc_message.body.decode())
        message = Message.model_validate(data)
        message_dict = message.model_dump()

        session: Session = get_session()

        participants = session.exec(
            select(ConversationParticipant)
            .where(ConversationParticipant.conversation_id == message.conversation_id)
        ).fetchall()

        for participant in participants:
            await manager.send_to_user(message_dict, participant.user_id)
    except Exception:
        logger.exception('Failed to bridge RMQ to WS')
