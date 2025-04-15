import uuid
from datetime import datetime
# from pydantic import EmailStr
from typing import Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB

class RoomCreate(SQLModel):
    name: str
    icon: str | None = Field(default=None)

class Room(RoomCreate, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

class Device(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    type: str
    sensor: bool
    room_id: uuid.UUID | None = Field(foreign_key="room.id")
    icon: str | None = Field(default=None)
    status: str | None = Field(default=None)
    value : Any = Field(sa_column = Column(JSONB))