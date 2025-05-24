import asyncio
import base64
import time
import numpy as np

from typing import Any, Optional, Tuple
from sqlmodel import select, Session

from app.core.config import settings
from app.core.db import get_embeddings_for_user, engine
from app.model import Camera, Device
from app.services.face_verification_service import face_service

class Modelizer:
    asr_pipeline = None
    tokenizer = None
    nlp_model = None

send_queue = asyncio.Queue()
model_ready = asyncio.Event()
AImodel = Modelizer()
aio = settings.ADAFRUIT_IO_CLIENT

def parse_value(raw: str) -> Any:
    if type(raw) is not str:
        pass
    lowered = raw.lower()
    if lowered == "true":
        return True
    elif lowered == "false":
        return False
    try:
        if '.' in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw  # fallback: string

# --- Hàm trợ giúp decode_base64_image và euclidean_distance_numpy (giữ nguyên) ---
def decode_base64_image(base64_string: str) -> Optional[bytes]:
    try:
        if "," in base64_string:
            header, data = base64_string.split(",", 1)
        else:
            data = base64_string
        return base64.b64decode(data)
    except Exception as e:
        print(f"Lỗi khi giải mã base64: {e}")
        return None

def euclidean_distance_numpy(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    if embedding1 is None or embedding2 is None:
        print("LỖI: Một trong hai embedding là None, không thể tính khoảng cách.")
        return float("inf")
    return float(np.sqrt(np.sum(np.square(embedding1 - embedding2))))

async def verify_face(user_id: str, image_base64: str) -> Tuple[bool, int, str | dict[str, Any]]: 
    user_id_to_verify = user_id
    # 1. Lấy embedding của ảnh mới cần kiểm tra
    new_image_bytes = decode_base64_image(image_base64)
    if not new_image_bytes:
        return False, 400, "Invalid base64 data for the image to check."

    new_embedding = face_service.get_embedding(new_image_bytes)
    if new_embedding is None:
        return False, 500, "Failed to extract embedding from the new image."

    # 2. Lấy DANH SÁCH embedding của user_id đã đăng ký
    stored_embeddings_list = get_embeddings_for_user(
        user_id_to_verify
    )

    if not stored_embeddings_list:  # Kiểm tra None hoặc list rỗng
        return False, 404, f"User ID '{user_id_to_verify}' not found or no embeddings registered."

    # 3. So sánh và Đếm số lần "Khớp"
    match_count = 0
    min_distance_found = float("inf")
    total_stored_embeddings = len(stored_embeddings_list)

    for stored_embedding in stored_embeddings_list:
        distance = euclidean_distance_numpy(new_embedding, stored_embedding)
        min_distance_found = min(
            min_distance_found, distance
        )  # Cập nhật khoảng cách nhỏ nhất

        if distance < settings.OPTIMAL_THRESHOLD:  # OPTIMAL_THRESHOLD từ config.py
            match_count += 1

    # 4. Tính Độ Tin Cậy (Confidence Score)
    confidence_score = (
        match_count / total_stored_embeddings if total_stored_embeddings > 0 else 0.0
    )

    # 5. Đưa ra Quyết định Cuối cùng is_same_person
    is_same_person = (
        confidence_score >= settings.CONFIDENCE_VERIFICATION_THRESHOLD
    )  # Từ config.py

    if is_same_person:
        message :dict[str, Any] = {
            "is_signed_person": user_id,
            "confidence_score": confidence_score,
            "min_distance_found": min_distance_found,
        } 
    else:
        message :str = "Not Correct Person"

    return True, 200, message

async def timing_task(device: dict[str, str], time_delay: int) -> None:
    time.sleep(time_delay)
    session = Session(engine)
    
    if device["device"] in ["light", "fan", "door"]:
        device_obj = session.exec(
            select(Device).where(Device.type == device["device"])
        ).first()
        if not device_obj:
            print(f"Device {device['device']} not found.")
            return
        device_obj.status = device["status"]
        if device["device"] == "light":
            device_obj.value = 1 if device["status"] == "on" else 0
        elif device["device"] == "door":
            device_obj.value = "ON" if device["status"] == "on" else "OFF"
        else:
            device_obj.value = 100 if device["status"] == "on" else 0
        await send_queue.put((device["device"], device_obj.value))
        session.add(device_obj)
        print(f"Device {device['device']} set to {device['status']} with value {device_obj.value}")
        session.commit()
        session.refresh(device_obj)
    else: 
        camera_obj = session.exec(select(Camera)).first()
        if not camera_obj:
            print("Camera not found.")
            return
        camera_obj.status = True if device["status"] == "on" else False
        session.add(camera_obj)
        print(f"Camera set to {device['status']}")
        session.commit()
        session.refresh(camera_obj)

    print(f"Task for {device['device']} completed after {time_delay} seconds.")
    session.close()