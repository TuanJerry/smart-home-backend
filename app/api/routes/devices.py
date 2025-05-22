import uuid
from typing import Any, Optional
from Adafruit_IO import Feed

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, delete, func, select

from app import crud
from app.Utils import parse_value
from app.api.deps import SessionDep
from app.core.config import settings
from app.model import (
    Device, Message, DeviceCreate, DevicePublic, DeviceUpdate
)
from app.websocket.manage import manager as ws_manage

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
        raise HTTPException(status_code=404, detail= f"Device with {id} not found")
    device = crud.device_update_lvalue(session=session, device=device)
    return device

@router.post(
    "/", response_model=Device
)
def device_create(*, session: SessionDep, device_create: DeviceCreate) -> Any:
    """
    Create new device.
    """
    new_feed = Feed(name = device_create.name, key = device_create.type)
    new_feed = aio.create_feed(new_feed)
    device = Device.model_validate(device_create, update={
        "id": str(new_feed.id),
        "sensor": False if device_create.type in ["fan", "light", "door"] else True,
        "value": 0,
        "status": "off" if device_create.type in ["fan", "light", "door"] else None,
    })
    aio.send(device.type, device.value)
    session.add(device)
    session.commit()
    session.refresh(device)
    print("Device created successfully")
    return device

@router.put(
    "/{id}", response_model=Device
)
async def device_update(
    id: str, *, session: SessionDep, device_update: DeviceUpdate
) -> Any:
    """
    Update a device by its ID.
    """
    up_device = session.get(Device, id)
    if not up_device:
        raise HTTPException(status_code=404, detail=f"Device with {id} not found")
    
    aio.send(up_device.type, device_update.value)
    await ws_manage.broadcast({
        "event": "device:value",
        "device_id": up_device.id,
        "status": "on",
        "value": device_update.value,
    })
    if device_update.status is None or device_update.status == "off":
        if (type(device_update.value) in [int, float] 
            or parse_value(device_update.value) > 0) or device_update.value == "ON":
            device_update.status = "on"
    update_part = device_update.model_dump(exclude_unset=True)
    up_device.sqlmodel_update(update_part)
    # device = Device.model_validate(up_device, update=device_update)
    session.add(up_device)
    session.commit()
    session.refresh(up_device)
    print(f"Device with {id} updated successfully")
    return up_device

@router.patch(
    "/{id}", response_model = Device
) 
async def device_toogle(
    id: str, *, session: SessionDep
) -> Any:
    """
    Toggle a device by its ID.
    """
    up_device = session.get(Device, id)
    if not up_device:
        raise HTTPException(status_code=404, detail=f"Device with {id} not found")
    
    if up_device.sensor:
        raise HTTPException(status_code=410, detail=f"Device with {id} is a sensor")
    else: 
        up_device.status = "on" if up_device.status == "off" else "off"
        if up_device.type == "door":
            up_device.value = "OFF" if up_device.status == "off" else "ON"
        elif up_device.type == "fan":
            up_device.value = 0 if up_device.status == "off" else 100
        elif up_device.type == "light":
            up_device.value = 0 if up_device.status == "off" else 1

    await ws_manage.broadcast({
        "event": "device:status",
        "device_id": up_device.id,
        "device_type": up_device.type,
        "status": up_device.status,
    })
    if up_device.type == "fan":
        await ws_manage.broadcast({
            "event": "device:value",
            "device_id": up_device.id,
            "value": up_device.value,
        })
    aio.send(up_device.type, up_device.value)
    # device = Device.model_validate(up_device, update=device_update)
    session.add(up_device)
    session.commit()
    session.refresh(up_device)
    print(f"Device with {id} updated successfully")
    return up_device

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
        raise HTTPException(status_code=404, detail=f"Device with {id} not found")
    
    aio.delete_feed(device.type)
    session.delete(device)
    session.commit()
    
    return Message(message="Device deleted successfully")

