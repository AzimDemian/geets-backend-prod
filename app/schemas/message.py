import uuid
from datetime import datetime

from sqlmodel import SQLModel, Field

class Message(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key='conversation.id')
    sender_id: uuid.UUID = Field(foreign_key='user.id')
    body: str
    created_at: datetime
    edited: bool = False
    deleted: bool = False
