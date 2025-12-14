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
    participant_ids: list[uuid.UUID] = Field(max_length=100)

@router.post('/create')
async def create_conversation(
    data: CreateConversationRequest,
    user_id: Annotated[uuid.UUID, Depends(get_token_user_id_http)],
    session: Session = Depends(get_session),
) -> Conversation:
    added_participants = session.exec(select(User.id).where(User.id.in_(data.participant_ids))).all()
    if len(added_participants) != len(data.participant_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Non-existing user(s)')

    is_group = len(added_participants) > 1

    conversation = Conversation(title=data.title, is_group=is_group)
    participants = []

    creating_participant = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=user_id,
        role=ParticipantRole.ADMIN if is_group else ParticipantRole.MEMBER,
    )
    participants.append(creating_participant)

    for new_participant_id in data.participant_ids:
        conversation_participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=new_participant_id,
        )
        participants.append(conversation_participant)

    session.add(conversation)
    session.add_all(participants)
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
