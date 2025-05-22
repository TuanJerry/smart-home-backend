import uuid
from datetime import datetime
# from pydantic import EmailStr
from typing import Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB

# Room settings
class RoomBase(SQLModel):
    name: str
    icon: str | None = Field(default=None)

class RoomCreate(RoomBase):
    pass

class Room(RoomBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

#Device settings
class DeviceBase(SQLModel):
    name: str
    type: str
    room_id: uuid.UUID | None = Field(default=None)
    icon: str | None = Field(default=None)
    status: str | None = Field(default=None)
    

class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase, table=True):
    id: str = Field(primary_key=True)
    sensor: bool
    room_id: uuid.UUID | None = Field(foreign_key="room.id")
    value : Any = Field(sa_column = Column(JSONB))

class DevicePublic(DeviceBase):
    id: str

class DeviceUpdate(DeviceBase):
    name: str | None = Field(default=None)
    type: str | None = Field(default=None)
    status: str | None = Field(default=None)
    value: Any | None = Field(sa_column = Column(JSONB))

# Generic message
class Message(SQLModel):
    message: str

# Environment settings
class Environment(SQLModel):
    temperature: float | None = Field(default=None)
    humidity: float | None = Field(default=None)
    lightLevel: float | None = Field(default=None)
    # airQuality: str

class Environment_metadata(Environment):
    temperature: list[dict[str, str]] | None = Field(default=None)
    humidity: list[dict[str, str]] | None = Field(default=None)
    lightLevel: list[dict[str, str]] | None = Field(default=None)