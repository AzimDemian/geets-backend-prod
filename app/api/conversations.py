import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from db.session import get_session
from schemas import Conversation, ConversationParticipant, Message, User
from schemas.conversation_participant import ParticipantRole
from sqlmodel import Session, select, desc
from utils.auth import get_token_user_id_http

router = APIRouter(prefix='/conversations')

class CreateConversationRequest(BaseModel):
    title: str = Field(max_length=100)
    other_id: uuid.UUID

@router.post('/create')
async def create_conversation(
    data: CreateConversationRequest,
    user_id: Annotated[uuid.UUID, Depends(get_token_user_id_http)],
    session: Session = Depends(get_session),
) -> Conversation:
    other = session.get(User, data.other_id)
    if not other:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Adding a non-existing user')

    conversation = Conversation(title=data.title)

    creating_participant = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=user_id,
    )
    
    other_participant = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=other.id,
    )

    session.add(conversation)
    session.add(creating_participant)
    session.add(other_participant)
    session.commit()
    session.refresh(conversation)

    return conversation

@router.get('')
async def get_conversations(
    user_id: Annotated[uuid.UUID, Depends(get_token_user_id_http)],
    session: Session = Depends(get_session),
) -> list[Conversation]:
    conversations = session.exec(
        select(ConversationParticipant.conversation_id.label('id'), Conversation.title, Conversation.is_group)
        .where(ConversationParticipant.user_id == user_id)
        .join(Conversation, Conversation.id == ConversationParticipant.conversation_id)
    ).all()

    return list(conversations)

@router.get('/{conversation_id}/messages')
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_token_user_id_http)],
    session: Session = Depends(get_session),
) -> list[Message]:
    conversation_participant = session.get(ConversationParticipant, (conversation_id, user_id))
    if not conversation_participant:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='You have no access to the conversation')
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.deleted == False)
        .order_by(desc(Message.created_at))
    ).all()
    return list(messages)
