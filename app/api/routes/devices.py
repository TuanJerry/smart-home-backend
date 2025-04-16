import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, delete, func, select

from app import crud
from app.Utils import parse_value
from app.api.deps import SessionDep

from app.core.config import settings
from app.model import (
    Device, Message, DeviceCreate, DevicePublic, DeviceUpdate, DeviceToggle
)
router = APIRouter(prefix="/devices", tags=["devices"])
aio = settings.ADAFRUIT_IO_CLIENT

@router.get(
    "/",
    response_model=list[DevicePublic],
)
def get_all_devices(session: SessionDep, skip: int = 0, limit: int = 100,
                    roomId: Optional[uuid.UUID] = Query(default=None)) -> Any:
    """
    Retrieve devices with optional filtering by roomId.
    """
    
    statement = select(Device)
    if roomId:
        statement = statement.where(Device.room_id == roomId)
    statement = statement.offset(skip).limit(limit)
    devices = session.exec(statement).all()
    
    for device in devices:
        device = crud.device_update_lvalue(session=session, device=device)

    return devices

@router.get(
    "/{id}", response_model=DevicePublic
)
def get_device_by_id(
    id: str, session: SessionDep
) -> Any:
    """
    Retrieve a device by its ID.
    """
    device = session.get(Device, id)
    if not device:
        raise HTTPException(status_code=404, detail="Device with {id} not found")
    device = crud.device_update_lvalue(session=session, device=device)
    return device

@router.post(
    "/", response_model=DeviceCreate
)
def device_create(*, session: SessionDep, device_create: DeviceCreate) -> Any:
    """
    Create new device.
    """
    new_feed = aio.create_feed(name = device_create.name, key = device_create.type)
    device = Device.model_validate(device_create, update={
        "id": new_feed.id,
        "sensor": False if device_create.type in ["fan", "light", "door"] else True,
    })
    session.add(device)
    session.commit()
    session.refresh(device)
    print("Device created successfully")
    return device

@router.put(
    "/{id}", response_model=DeviceUpdate
)
def device_update(
    id: str, *, session: SessionDep, device_update: DeviceUpdate
) -> Any:
    """
    Update a device by its ID.
    """
    up_device = session.get(Device, id)
    if not up_device:
        raise HTTPException(status_code=404, detail="Device with {id} not found")
    
    aio.send(up_device.type, device_update.value)
    if device_update.status:
        if (isinstance(device_update.value, (int, float)) 
            and parse_value(device_update.value) > 0) or device_update.value == "ON":
            device_update.status = "on"
    device = Device.model_validate(up_device, update=device_update)
    session.add(device)
    session.commit()
    session.refresh(device)
    print("Device with {id} updated successfully")
    return device

@router.patch(
    "/{id}", response_model = DeviceToggle
) 
def device_toogle(
    id: str, *, session: SessionDep, device_update: DeviceToggle
) -> Any:
    """
    Toggle a device by its ID.
    """
    up_device = session.get(Device, id)
    if not up_device:
        raise HTTPException(status_code=404, detail="Device with {id} not found")
    
    if up_device.sensor:
        raise HTTPException(status_code=410, detail="Device with {id} is a sensor")
    else: 
        if up_device.type not in ["door"]:
            up_device.value = 0 if device_update.status == "off" else up_device.value
        else: 
            up_device.value = "OFF" if device_update.status == "off" else "ON"
    aio.send(up_device.type, up_device.value)
    device = Device.model_validate(up_device, update=device_update)
    session.add(device)
    session.commit()
    session.refresh(device)
    print("Device with {id} updated successfully")
    return device

@router.delete(
    "/{id}",
    response_model=Message,
)
def device_delete(
    id: str, *, session: SessionDep
) -> Any:
    """
    Delete a device by its ID.
    """
    device = session.get(Device, id)
    if not device:
        raise HTTPException(status_code=404, detail="Device with {id} not found")
    
    aio.delete_feed(device.type)
    session.delete(device)
    session.commit()
    
    return Message(message="Device deleted successfully")

