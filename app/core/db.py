from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.model import Room, RoomCreate, Device

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
# aio = settings.ADAFRUIT_IO_CLIENT


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    # Initialize the first database 
    first_room = session.exec(
        select(Room).where(Room.name == "Living Room")
    ).first()
    if not first_room:
        first_room = RoomCreate(
            name = "Living Room",
            icon = None,
        )
        room = crud.create_room(session=session, room_create=first_room)
    else: 
        room = first_room

    print(room)
    check_device = session.exec(
        select(Device).where(Device.room_id == room.id)
    ).first()
    if not check_device:
        list_device = crud.setting_device(session=session, room=room)
        print(list_device)

