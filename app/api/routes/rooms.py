import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.model import Room, RoomCreate, Message

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/", response_model=list[Room])
def all_rooms_info(
    session: SessionDep, skip: int = 0, limit: int = 10
) -> Any:
    """
    Show all rooms.
    """

    statement = select(Room).offset(skip).limit(limit)
    rooms = session.exec(statement).all()
    return rooms

@router.get("/{id}", response_model=Room)
def Id_room_info(session: SessionDep, id: uuid.UUID) -> Any:
    """
    Get room by ID.
    """
    room = session.get(Room, id)
    if not room:
        raise HTTPException(status_code=404, detail="Room with {id} not found")
    return room


@router.post("/", response_model=RoomCreate)
def room_create(
    *, session: SessionDep, room_create: RoomCreate
) -> Any:
    """
    Create new room.
    """
    room = Room.model_validate(room_create, update={"id": uuid.uuid4()})
    session.add(room)
    session.commit()
    session.refresh(room)
    print("Room created successfully")
    return room


@router.put("/{id}", response_model=RoomCreate)
def room_update(
    *,
    session: SessionDep,
    id: uuid.UUID,
    room_create: RoomCreate,
) -> Any:
    """
    Update an room.
    """
    room = session.get(Room, id)
    if not room:
        raise HTTPException(status_code=404, detail="Room with {id} not found")
    update_dict = room_create.model_dump(exclude_unset=True)
    room.sqlmodel_update(update_dict)
    session.add(room)
    session.commit()
    session.refresh(room)
    print("Room id: {id} has been updated")
    return room


@router.delete("/{id}")
def room_delete(
    session: SessionDep, id: uuid.UUID
) -> Message:
    """
    Delete an room.
    """
    item = session.get(Room, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item with {id} not found")
    session.delete(item)
    session.commit()
    return Message(message="Room deleted successfully")
