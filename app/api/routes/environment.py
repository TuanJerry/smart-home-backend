from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from app.api.deps import SessionDep

from app.ada_fetchinfo import get_last_value, get_all_value
from app.model import Device, Environment, Environment_metadata
from app.utils import aio

router = APIRouter(prefix="/environment", tags=["environment"])
@router.get("/", response_model=Environment)
def get_envi_data(
    session: SessionDep
) -> Any:
    """
    Environment data fetch.
    """
    sensors = session.exec(
        select(Device).where(Device.sensor == True).order_by(func.random())
    ).all()
    if not sensors:
        raise HTTPException(status_code=404, detail="No sensors found")
    
    envi = Environment()
    for sensor in sensors:
        if sensor.type == "temperature-sensor": 
            envi.temperature = get_last_value(sensor.type)["value"]
        elif sensor.type == "humidity-sensor":
            envi.humidity = get_last_value(sensor.type)["value"]
        elif sensor.type == "light-sensor":
            envi.lightLevel = get_last_value(sensor.type)["value"]
    return envi

@router.get("/all", response_model=Environment_metadata)
def get_all_envi_data(
    session: SessionDep
) -> Any:
    sensors = session.exec(
        select(Device).where(Device.sensor == True).order_by(func.random())
    ).all()
    if not sensors:
        raise HTTPException(status_code=404, detail="No sensors found")
    
    envi = Environment_metadata()
    for sensor in sensors:
        if sensor.type == "temperature-sensor": 
            envi.temperature = get_all_value(sensor.type)
        elif sensor.type == "humidity-sensor":
            envi.humidity = get_all_value(sensor.type)
        elif sensor.type == "light-sensor":
            envi.lightLevel = get_all_value(sensor.type)
    return envi

@router.put("/", response_model=Environment)
def update_item(
    *,
    session: SessionDep,
    envi_set: Environment,
) -> Any:
    """
    Update environment data(For test).
    """
    sensors = session.exec(
        select(Device).where(Device.sensor == True).order_by(func.random())
    ).all()
    if not sensors:
        raise HTTPException(status_code=404, detail="No sensors found")
    for sensor in sensors:
        if sensor.type == "temperature-sensor":
            if envi_set.temperature is not None:
                aio.send_data(sensor.type, envi_set.temperature)
                sensor.value = envi_set.temperature
            else:
                envi_set.temperature = sensor.value
        elif sensor.type == "humidity-sensor":
            if envi_set.humidity is not None:
                aio.send_data(sensor.type, envi_set.humidity)
                sensor.value = envi_set.humidity
            else:
                envi_set.humidity = sensor.value
        elif sensor.type == "light-sensor":
            if envi_set.lightLevel is not None:
                aio.send_data(sensor.type, envi_set.lightLevel)
                sensor.value = envi_set.lightLevel 
            else:
                envi_set.lightLevel = sensor.value

    session.add_all(sensors)
    session.commit()
    for sensor in sensors:
        session.refresh(sensor) 
    print("Environment data updated successfully")
    return envi_set
