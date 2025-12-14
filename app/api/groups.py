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

router = APIRouter(prefix='/groups')

class CreateGroupRequest(BaseModel):
    title: str = Field(max_length=100)
    participant_ids: list[uuid.UUID] = Field(max_length=100)

@router.post('/create')
async def create_group(
    data: CreateGroupRequest,
    user_id: Annotated[uuid.UUID, Depends(get_token_user_id_http)],
    session: Session = Depends(get_session),
) -> Conversation:
    added_participants = session.exec(select(User.id).where(User.id.in_(data.participant_ids))).all()
    if len(added_participants) != len(data.participant_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Adding non-existing user(s)')

    group = Conversation(title=data.title, is_group=True)
    participants = []

    creating_participant = ConversationParticipant(
        conversation_id=group.id,
        user_id=user_id,
        role=ParticipantRole.ADMIN,
    )
    participants.append(creating_participant)

    for new_participant_id in data.participant_ids:
        conversation_participant = ConversationParticipant(
            conversation_id=group.id,
            user_id=new_participant_id,
        )
        participants.append(conversation_participant)

    session.add(group)
    session.add_all(participants)
    session.commit()
    session.refresh(group)

    return group
