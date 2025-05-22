import asyncio, time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select, Session

from app import crud
from app.core.db import engine
from app.ada_fetchinfo import get_last_value
from app.model import Device
from app.websocket.manage import manager

def get_sensor_value(session: Session, sensor_type: str) -> float | None:
    sensor = session.exec(
        select(Device).where(Device.type == sensor_type)
    ).first()
    crud.device_update_lvalue(session=session, device=sensor)
    if not sensor:
        return None
    return get_last_value(sensor_type)["value"]

router = APIRouter(prefix="/environment", tags=["environment"])

@router.websocket("/")
async def update_environment(websocket: WebSocket):
    await manager.connect(websocket)
    session = Session(engine)

    prev_temp = prev_humid = prev_light = None
    last_sent = {
        "temperature": 0,
        "humidity": 0,
        "light": 0
    }
    throttle_interval = 2  # giây

    while True:
        try:
            now = time.time()

            temp = get_sensor_value(session, "temperature-sensor")
            humid = get_sensor_value(session, "humidity-sensor")
            light = get_sensor_value(session, "light-sensor")

            if temp != prev_temp and now - last_sent["temperature"] >= throttle_interval:
                await manager.broadcast({
                    "event": "environment:temperature",
                    "value": temp
                })
                prev_temp = temp
                last_sent["temperature"] = now

            if humid != prev_humid and now - last_sent["humidity"] >= throttle_interval:
                await manager.broadcast({
                    "event": "environment:humidity",
                    "value": humid
                })
                prev_humid = humid
                last_sent["humidity"] = now

            if light != prev_light and now - last_sent["light"] >= throttle_interval:
                await manager.broadcast({
                    "event": "environment:light",
                    "value": light
                })
                prev_light = light
                last_sent["light"] = now

            await asyncio.sleep(2)  # điều chỉnh phù hợp
            await manager.waiting(websocket)
        except WebSocketDisconnect:
            manager.disconnect(websocket)  
            break;
        finally:
            session.close()