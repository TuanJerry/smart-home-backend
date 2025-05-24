import asyncio
import base64
import numpy as np

from typing import Any, Optional, Tuple
from app.core.config import settings
from app.core.db import get_embeddings_for_user
from app.services.face_verification_service import face_service

send_queue = asyncio.Queue()
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