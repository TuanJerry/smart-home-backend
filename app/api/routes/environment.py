from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from app.api.deps import SessionDep

from app.ada_fetchinfo import get_last_value
from app.core.config import settings
from app.model import Device, Environment

router = APIRouter(prefix="/environment", tags=["environment"])
aio = settings.ADAFRUIT_IO_CLIENT

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
        elif sensor.type == "humidity-sensor":
            if envi_set.humidity is not None:
                aio.send_data(sensor.type, envi_set.humidity)
                sensor.value = envi_set.humidity
        elif sensor.type == "light-sensor":
            if envi_set.lightLevel is not None:
                aio.send_data(sensor.type, envi_set.lightLevel)
                sensor.value = envi_set.lightLevel
        
    session.add_all(sensors)
    session.commit()
    session.refresh(sensors)
    print("Environment data updated successfully")
    return envi_set
