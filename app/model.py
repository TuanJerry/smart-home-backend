import uuid
from datetime import datetime
# from pydantic import EmailStr
from typing import Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB

class RoomBase(SQLModel):
    name: str
    icon: str | None = Field(default=None)

class RoomCreate(RoomBase):
    pass

class Room(RoomBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class DeviceBase(SQLModel):
    id: str 
    name: str
    type: str
    room_id: uuid.UUID | None = Field(default=None)
    status: str | None = Field(default=None)
    icon: str | None = Field(default=None)
    value : Any = Field(sa_column = Column(JSONB))

class DeviceCreate(DeviceBase):
    name: str
    type: str
    room_id: uuid.UUID | None = Field(default=None)
    icon: str | None = Field(default=None)

class Device(DeviceBase, table=True):
    id: str = Field(primary_key=True)
    sensor: bool
    room_id: uuid.UUID | None = Field(foreign_key="room.id")

class DevicePublic(DeviceBase):
    pass

class DeviceUpdate(DeviceBase):
    name: str
    status: str
    value: Any = Field(sa_column = Column(JSONB))

class DeviceToggle(DeviceBase):
    status: str

# Generic message
class Message(SQLModel):
    message: str

# Environment settings
class Environment(SQLModel):
    temperature: float | None = Field(default=None)
    humidity: float | None = Field(default=None)
    lightLevel: float | None = Field(default=None)
    # airQuality: str
