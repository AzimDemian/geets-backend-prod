import uuid

from sqlmodel import SQLModel, Field

class WSRequest(SQLModel, table=False):
    type: str
    payload: dict


class WSMessageCreate(SQLModel, table=False):
    conversation_id: uuid.UUID
    body: str = Field(max_length=10000)


class WSMessageEdit(SQLModel, table=False):
    id: uuid.UUID
    new_body: str = Field(max_length=10000)


class WSMessageDelete(SQLModel, table=False):
    id: uuid.UUID
