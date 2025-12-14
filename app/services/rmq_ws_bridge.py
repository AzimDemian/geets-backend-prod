import json
import logging
import uuid

import aio_pika
from sqlmodel import Session, select

from db.session import get_session
from schemas import ConversationParticipant, Message
from ws.connection import manager

logger = logging.getLogger(__name__)

async def rmq_ws_bridge(inc_message: aio_pika.IncomingMessage) -> None:
    async with inc_message.process():
        try:
            data = json.loads(inc_message.body.decode())
            event_type, payload = data['type'], data['payload']
            message = Message.model_validate(payload)
            message_str = message.model_dump_json()
            message_dict = json.loads(message_str)

            session: Session = next(get_session())

            participants = session.exec(
                select(ConversationParticipant)
                .where(ConversationParticipant.conversation_id == message.conversation_id)
            ).all()

            out = {
                'type': event_type,
                'payload': message_dict,
            }

            for participant in participants:
                await manager.send_to_user(out, participant.user_id)
        except Exception:
            logger.exception('Failed to bridge RMQ to WS')