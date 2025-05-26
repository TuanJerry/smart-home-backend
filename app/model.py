import uuid
import datetime
from typing import Any, Optional
from sqlmodel import Field, SQLModel, Column, String
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

# Room settings
class RoomBase(SQLModel):
    name: str
    icon: str | None = Field(default=None)

class RoomCreate(RoomBase):
    pass

class Room(RoomBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

#Device settings
class DeviceBase(SQLModel):
    name: str
    type: str
    room_id: uuid.UUID | None = Field(default=None)
    icon: str | None = Field(default=None)
    status: str | None = Field(default=None)
    
class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase, table=True):
    id: str = Field(primary_key=True)
    sensor: bool
    room_id: uuid.UUID | None = Field(foreign_key="room.id")
    value : Any = Field(sa_column = Column(JSONB))

class DevicePublic(DeviceBase):
    id: str
    value: Any | None = Field(default=None)

class DeviceUpdate(DeviceBase):
    name: str | None = Field(default=None)
    type: str | None = Field(default=None)
    status: str | None = Field(default=None)
    value: Any | None = Field(sa_column = Column(JSONB))

# Generic message
class Message(SQLModel):
    message: str

class ErrorResponse(SQLModel):
    detail: str

# Environment settings
class Environment(SQLModel):
    temperature: float | None = Field(default=None)
    humidity: float | None = Field(default=None)
    lightLevel: float | None = Field(default=None)
    # airQuality: str

class Environment_metadata(Environment):
    temperature: list[dict[str, str]] | None = Field(default=None)
    humidity: list[dict[str, str]] | None = Field(default=None)
    lightLevel: list[dict[str, str]] | None = Field(default=None)

# Camera settings 
class CameraBase(SQLModel):
    name: str
    room_id: uuid.UUID | None = Field(default=None)
    status: bool = Field(default=True)  # Trạng thái camera (on/off)

class CameraCreate(CameraBase):
    pass

class Camera(CameraBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID | None = Field(foreign_key="room.id")
    user_ids: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))  # Danh sách ID người dùng đã đăng ký 

class CameraUpdate(SQLModel):
    user_id: str # ID của người dùng đã đăng ký

class CameraPublic(CameraBase):
    name: str
    room_id: uuid.UUID | None = Field(default=None)
    status: bool 
    user_ids: list[str] | None = Field(default_factory=list) 

# Camera metadata Face Verification settings
class ImageInput(SQLModel):
    image_base64: str  # Chuỗi base64 của ảnh

class FaceRegistrationRequest(SQLModel):
    user_id: str
    image_base64: str

class FaceRegistrationResponse(SQLModel):
    message: str
    user_id: str
    # file_path: Optional[str] = None # Tùy chọn nếu bạn muốn trả về nơi lưu ảnh/embedding

class FaceVerificationRequest(SQLModel):
    camera_verify_id: uuid.UUID  # ID của camera xác thực
    image_base64_to_check: str  # Ảnh mới cần kiểm tra

class FaceVerificationResponse(SQLModel):
    is_signed_person: str
    confidence_score: float  
    min_distance_found: Optional[float] = (
        None  # << THAY ĐỔI/LÀM RÕ: Khoảng cách nhỏ nhất tìm được
    )
    # Có thể là None nếu không có embedding nào để so sánh
    # distance: float # Có thể bỏ trường distance cũ này nếu min_distance_found và confidence_score là đủ
    threshold_used_for_distance: float  # Ngưỡng dùng để so sánh từng cặp embedding
    confidence_threshold_used: (
        float  # Ngưỡng dùng để quyết định is_same_person từ confidence_score
    )

# Voice settings
class HistoryBase(SQLModel):
    stt: int = Field(primary_key=True, default=None)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )

class HistoryCreate(SQLModel):
    request: str

class HistoryVoice(HistoryBase, table=True):
    request: str
    response: str

class HistoryPublic(SQLModel):
    request: str
    response: str
    created_at: datetime.datetime 