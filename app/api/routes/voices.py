from typing import Any

from sqlmodel import select
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.model import HistoryVoice, HistoryPublic, HistoryCreate, Message, Device, Camera
from app.utils import AImodel, send_queue, model_ready, timing_task
from app.api.deps import SessionDep
from app.services.voice_recording_service import voice_service

router = APIRouter(prefix="/voices", tags=["voices"])
@router.get(
    "/",
    response_model=list[HistoryPublic],
    summary="Get all voice history",
)
def get_all_history(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve all voice history.
    """
    statement = session.exec(HistoryVoice.select()).offset(skip).limit(limit)
    history = statement.all()
    return history

@router.get(
    "/transcript",
    response_model=Message,
    summary="Get voice transcript",
)
async def transcribe():
    audio_path, start_time = voice_service.record_audio()

    if not audio_path:
        raise HTTPException(status_code=500, detail="Failed to record audio. Try again!")
    await model_ready.wait()  # ✅ Chờ mô hình sẵn sàng
    message = AImodel.asr_pipeline(audio_path)
    if not message:
        raise HTTPException(status_code=400, detail="Failed to transcribe audio.")
    return Message(message=message["text"])

@router.post(
    "/voice_logic",
    response_model=HistoryPublic,
    summary="handle logic for voice commands",
)
async def handle_voice_logic(
    *,
    session: SessionDep,
    voice_command: HistoryCreate,
    background_tasks: BackgroundTasks,
) -> HistoryPublic:
    """
    Handle logic for voice commands.
    """
    if not voice_command.request:
        raise HTTPException(status_code=404, detail="Voice command cannot be empty.")
    message = await voice_service.nlp_pipeline(voice_command.request)
    if not message:
        raise HTTPException(status_code=404, detail="Failed to process voice command.")
    print(f"Message: {message}")
    
    work_respone : str = message["intent"]
    work_condition : dict = message["condition"]

    # 1. Xác định những thiết bị sẽ được xử lý trên intent
    work_devices = []
    work_confirm = True
    fan_speed = 0
    time_delay = 0
    mapping = {
        "LIGHT": "light",
        "FAN": "fan",
        "DOOR": "door",
        "FACE_DETECTION": "camera"
    } 
    status_map = {
        "TURN_ON": "on",
        "TURN_OFF": "off",
        "OPEN": "on",     # OPEN_DOOR = on
        "CLOSE": "off"    # CLOSE_DOOR = off
    }
    actions = work_respone.split("_AND_")
    for action in actions:
        for status_key in status_map:
            if action.startswith(status_key):
                device_key = action[len(status_key) + 1:]
                device = mapping.get(device_key, device_key.lower())
                work_devices.append({
                    "device": device,
                    "status": status_map[status_key]
                })
                break
    # 2. Xác định các giá trị điều kiện để thực hiện logic hoặc timing để chạy background task
    if work_condition:
        if work_condition["sensor"] in ["temperature", "humidity", "light"]:
            mapping_sensor = {
                "temperature": "temperature-sensor",
                "humidity": "humidity-sensor",
                "light": "light-sensor"
            }
            sensor = session.exec(
                select(Device).where(Device.type == mapping_sensor[work_condition["sensor"]])
            ).first()
            if not sensor:
                raise HTTPException(status_code=404, detail=f"Sensor {work_condition['sensor']} not found.")
            if work_condition["op"] == '>':
                work_confirm = False if sensor.value <= work_condition["value"] else True
            elif work_condition["op"] == '<':
                work_confirm = False if sensor.value >= work_condition["value"] else True
            else: 
                work_confirm = False if sensor.value != work_condition["value"] else True
        elif work_condition["sensor"] == "fan": 
            work_confirm = True 
            fan_speed = work_condition["value"]
        else:
            work_confirm = True
            time_delay = work_condition["value"]
     # 3. Thực hiện logic với các thiết bị nếu work_confirm là True
    if work_confirm: 
        if time_delay > 0:
            for device in work_devices:
                background_tasks.add_task(timing_task, device, time_delay)
                print(f"Scheduling {device['device']}'s action to be done after {time_delay} seconds.")
        else:
            for device in work_devices:
                if device["device"] in ["light", "fan", "door"]:
                    device_obj = session.exec(
                        select(Device).where(Device.type == device["device"])
                    ).first()
                    if not device_obj:
                        raise HTTPException(status_code=404, detail=f"Device {device['device']} not found.")
                    device_obj.status = device["status"]
                    if device["device"] == "light":
                        device_obj.value = 1 if device["status"] == "on" else 0
                    elif device["device"] == "door":
                        device_obj.value = "ON" if device["status"] == "on" else "OFF"
                    else:
                        if device["status"] == "on":
                            device_obj.value = fan_speed if fan_speed > 0 else 100
                        else: 
                            device_obj.value = fan_speed
                    await send_queue.put((device["device"], device_obj.value))
                    session.add(device_obj)
                    print(f"Device {device['device']} set to {device['status']} with value {device_obj.value}")
                    session.commit()
                    session.refresh(device_obj)
                else: 
                    camera_obj = session.exec(select(Camera)).first()
                    if not camera_obj:
                        raise HTTPException(status_code=404, detail="Camera not found.")
                    camera_obj.status = True if device["status"] == "on" else False
                    session.add(camera_obj)
                    print(f"Camera set to {device['status']}")
                    session.commit()
                    session.refresh(camera_obj)
    else: 
        work_respone = "NO ACTION TAKEN DUE TO CONDITION NOT MET"

    history = HistoryVoice(
        request=voice_command.request,
        response=work_respone,
    )
    session.add(history)
    session.commit()
    session.refresh(history)
    print(f"History saved: request={history.request}, response={history.response}, created_at={history.created_at}")
    return HistoryPublic(
        request=history.request,
        response=history.response,
        created_at=history.created_at
    )

@router.delete(
    "/",
    response_model=Message,
    summary="Delete all voice history"
)
def delete_all_history(
    session: SessionDep,
) -> Any:
    """
    Delete all voice history.
    """
    session.exec(HistoryVoice.delete())
    session.commit()
    return Message(message="All voice history deleted successfully.")
