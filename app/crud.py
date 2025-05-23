import uuid
from typing import Any
from app.utils import parse_value

from sqlmodel import Session, delete
from app.core.config import settings
from app.ada_fetchinfo import get_last_value

# from app.core.security import get_password_hash, verify_password
from app.model import RoomCreate, Room, Device

def create_room(*, session: Session, room_create: RoomCreate) -> Room:
    db_obj = Room.model_validate(room_create)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def setting_device(*, session: Session, room: Room) -> list[Device]:
    session.exec(delete(Device))
    aio = settings.ADAFRUIT_IO_CLIENT
    feeds = aio.feeds()
    list_device = []
    for feed in feeds:
        id = str(feed.id)
        name = feed.name
        type = feed.key
        sensor = False if type in ["fan", "light", "door"] else True
        icon = None
        value = parse_value(get_last_value(feed.key)["value"])
        if not sensor: 
            room_id = room.id
            status = "on" if ((isinstance(value, (int, float)) and value > 0) 
                                    or value == "ON") else "off"
        else: 
            room_id = None
            status = None
        db_obj = Device(
            **{
                "id": id,
                "name": name,
                "type": type,
                "sensor": sensor,
                "room_id": room_id,
                "icon": icon,
                "status": status,
                "value": value
            }      
        )  
        session.add(db_obj)
        list_device.append(db_obj)
        session.commit()
        session.refresh(db_obj)
    return list_device    

def device_update_lvalue(*, session: Session, device: Device) -> Device:
    device.value = parse_value(get_last_value(device.type)["value"])
    session.add(device)
    session.commit()
    session.refresh(device)
    return device

# def create_user(*, session: Session, user_create: UserCreate) -> User:
#     db_obj = User.model_validate(
#         user_create, update={"hashed_password": get_password_hash(user_create.password)}
#     )
#     session.add(db_obj)
#     session.commit()
#     session.refresh(db_obj)
#     return db_obj


# def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
#     user_data = user_in.model_dump(exclude_unset=True)
#     extra_data = {}
#     if "password" in user_data:
#         password = user_data["password"]
#         hashed_password = get_password_hash(password)
#         extra_data["hashed_password"] = hashed_password
#     db_user.sqlmodel_update(user_data, update=extra_data)
#     session.add(db_user)
#     session.commit()
#     session.refresh(db_user)
#     return db_user


# def get_user_by_email(*, session: Session, email: str) -> User | None:
#     statement = select(User).where(User.email == email)
#     session_user = session.exec(statement).first()
#     return session_user


# def authenticate(*, session: Session, email: str, password: str) -> User | None:
#     db_user = get_user_by_email(session=session, email=email)
#     if not db_user:
#         return None
#     if not verify_password(password, db_user.hashed_password):
#         return None
#     return db_user


# def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
#     db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
#     session.add(db_item)
#     session.commit()
#     session.refresh(db_item)
#     return db_item
