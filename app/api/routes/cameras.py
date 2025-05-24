import uuid 
import numpy as np

from typing import Any, Optional, List, Tuple
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.db import get_all_user_ids, add_embedding, get_embeddings_for_user
from app.services.face_verification_service import face_service
from app.utils import decode_base64_image, verify_face, send_queue
from app.model import (
    CameraPublic, Camera, CameraCreate, Message, CameraUpdate, Device,
    FaceRegistrationRequest,
    FaceRegistrationResponse,
    FaceVerificationRequest,
    FaceVerificationResponse,
    ErrorResponse 
)

router = APIRouter(prefix="/cameras", tags=["cameras"])
@router.get(
    "/",
    response_model=list[CameraPublic]
)
def get_all_cameras(session: SessionDep, skip: int = 0, limit: int = 100,
                     roomId: Optional[uuid.UUID] = Query(default=None)) -> Any:
    """
    Retrieve cameras with optional filtering by roomId.
    """
    
    statement = select(Camera)
    if roomId:
        statement = statement.where(Camera.room_id == roomId)
    statement = statement.offset(skip).limit(limit)
    cameras = session.exec(statement).all()
    
    return cameras

@router.get(
    "/camera/{id}", response_model=Camera
)
def get_camera_by_id(
    id: str, session: SessionDep
) -> Any:
    """
    Retrieve a camera by its ID.
    """
    camera = session.get(Camera, id)
    if not camera:
        raise HTTPException(status_code=404, detail= f"Camera with {id} not found")
    return camera

@router.get(
    "/all_users",
    response_model=List[str]
)
async def get_all_users():
    return get_all_user_ids()

@router.post(
    "/", response_model=Camera
)
def camera_create(*, session: SessionDep, camera_create: CameraCreate) -> Any:
    """
    Create new camera.
    """
    camera = Camera.model_validate(camera_create, update={"id": uuid.uuid4()})
    session.add(camera)
    session.commit()
    session.refresh(camera)
    print("Camera created successfully")
    return camera

@router.post(
    "/register_face",
    response_model=FaceRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a face by adding its embedding to the user's list",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid image data or user ID",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Failed to process image or save embedding",
        },
    },
)
async def register_face(request_data: FaceRegistrationRequest):
    user_id_cleaned = request_data.user_id.strip()
    if not user_id_cleaned: 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID cannot be empty or just whitespace.",
        )
    image_bytes = decode_base64_image(request_data.image_base64)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base64 image data."
        )

    embedding = face_service.get_embedding(image_bytes)
    if embedding is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract embedding from the image.",
        )

    success = add_embedding(
        user_id_cleaned, embedding
    ) 
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save embedding to store.",
        )

    current_user_embeddings = get_embeddings_for_user(
        user_id_cleaned
    )  
    num_embeddings_for_user = (
        len(current_user_embeddings) if current_user_embeddings else 0
    )

    return FaceRegistrationResponse(
        message=f"Embedding added for user {user_id_cleaned}. User now has {num_embeddings_for_user} registered embedding(s).",  # <<< SỬA Ở ĐÂY >>>
        user_id=user_id_cleaned
    )

@router.post(
    "/verify_face",
    response_model=FaceVerificationResponse | Message,
    summary="Verify a face against a registered user ID using multiple stored embeddings",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid image data or user ID",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Registered user ID not found or no embeddings",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Failed to process image",
        },
    },
)
async def camera_identification(request_data: FaceVerificationRequest, session: SessionDep):
    """
    Xác thực khuôn mặt với user_id đã đăng ký của camera để quyết định mở cửa hay không.
    So sánh embedding của ảnh mới với TẤT CẢ embedding đã lưu của user_id đó.
    Tính confidence score và đưa ra quyết định.
    """
    camera = session.get(Camera, request_data.camera_verify_id)
    final_message = Message(message="The user is not registered in the system. Door can't be opened.")
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera with ID {request_data.camera_verify_id} not found")
    if not camera.status:
        raise HTTPException(status_code=400, detail="Camera is not active")
    for user_id in camera.user_ids:
        result: Tuple[bool, int, str | dict[str, Any]] = await verify_face(
            user_id=user_id,
            image_base64=request_data.image_base64_to_check
        )
        success, status_code, message = result
        if not success:
            raise HTTPException(
                status_code=status_code,
                detail=message
            )
        if type(message) is dict:
            min_distance_found = message.get("min_distance_found")
            final_message = FaceVerificationResponse(
                is_signed_person= message.get("is_signed_person"),
                confidence_score= message.get("confidence_score"),
                min_distance_found=(
                    min_distance_found if min_distance_found != float("inf") else None
                ),
                threshold_used_for_distance=settings.OPTIMAL_THRESHOLD,
                confidence_threshold_used=settings.CONFIDENCE_VERIFICATION_THRESHOLD
            )
            break
    if type(final_message) is FaceVerificationResponse:
        door_device = session.exec(
            select(Device).where(Device.type == "door" and Device.room_id == camera.room_id)
        ).first()
        if not door_device:
            raise HTTPException(status_code=404, detail=f"Door of {camera.room_id} not found")
        if door_device.status == "off":
            door_device.status = "on"
            door_device.value = "ON"
            await send_queue.put((door_device.type, door_device.value))
            session.add(door_device)
            session.commit()
            session.refresh(door_device)
            print(f"Door with {door_device.id} opened successfully")
        else:
            print(f"Door with {door_device.id} is already open")
    return final_message

@router.put(
    "/{id}", response_model=Camera
)
def update_user(
    id: str, session: SessionDep, camera_update: CameraUpdate,
    delete: Optional[bool] = Query(default=False)
) -> Any:
    """
    Update a camera by its ID.
    """
    camera = session.get(Camera, id)
    if not camera:
        raise HTTPException(status_code=404, detail= f"Camera with {id} not found")
    if not camera.status:
        raise HTTPException(status_code=400, detail="Camera is not active")
    user = get_all_user_ids()
    if camera_update.user_id not in user:
        raise HTTPException(status_code=404, detail="User not found")
    if delete:
        if camera_update.user_id not in camera.user_ids:
            raise HTTPException(status_code=400, detail="User not registered")
        camera.user_ids.remove(camera_update.user_id)
    else:
        if camera_update.user_id in camera.user_ids:
            raise HTTPException(status_code=400, detail="User already registered")
        camera.user_ids.append(camera_update.user_id)
        print(f"User {camera_update.user_id} added to camera {id}. User IDs: {camera.user_ids}")
    flag_modified(camera, "user_ids")
    session.add(camera)
    session.commit()
    session.refresh(camera)
    # print(f"Camera Information: {camera.id}, Name: {camera.name}, Room ID: {camera.room_id}, User IDs: {camera.user_ids}")
    return camera

@router.patch(
    "/{id}", response_model=CameraPublic
)
def toggle_camera(
    id: str, session: SessionDep
) -> CameraPublic:
    """
    Toggle the status of a camera by its ID.
    """
    camera = session.get(Camera, id)
    if not camera:
        raise HTTPException(status_code=404, detail= f"Camera with {id} not found")
    
    camera.status = not camera.status
    session.add(camera)
    session.commit()
    session.refresh(camera)
    
    print(f"Camera with {id} toggled successfully. New status: {'on' if camera.status else 'off'}")
    return CameraPublic(
        name=camera.name,
        room_id=camera.room_id,
        status=camera.status,
        user_ids=camera.user_ids
    )

@router.delete(
    "/{id}", response_model=Message
)
def delete_camera(
    id: str, session: SessionDep
) -> Message:
    """
    Delete a camera by its ID.
    """
    camera = session.get(Camera, id)
    if not camera:
        raise HTTPException(status_code=404, detail= f"Camera with {id} not found")
    
    session.delete(camera)
    session.commit()
    return Message(message=f"Camera with {id} deleted successfully")