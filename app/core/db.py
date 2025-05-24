import json
import numpy as np
from pathlib import Path

from typing import Dict, Optional, List, Any  # Thêm Any
from sqlmodel import Session, create_engine, select

# from app import crud
from app.core.config import settings
from app.model import Room, RoomCreate, Device

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
store_path = settings.EMBEDDINGS_STORE_PATH
store_dir = settings.EMBEDDINGS_STORE_DIR.mkdir(parents=True, exist_ok=True)

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

def load_store() -> Dict[str, List[List[float]]]:
    """Tải dữ liệu embeddings từ file JSON."""
    if store_path.exists():
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Đảm bảo value của mỗi key là một list (có thể chứa các list embedding)
                for user_id, embeddings in data.items():
                    if not isinstance(embeddings, list):
                        print(
                            f"Dữ liệu cho user_id '{user_id}' trong store không phải là list, bỏ qua user này."
                        )
                        # Có thể xóa key này hoặc xử lý khác: data[user_id] = []
                        continue  # Bỏ qua user này nếu định dạng không đúng
                    # Kiểm tra sâu hơn (tùy chọn): mỗi item trong list embedding có phải là list of numbers
                    for emb_list in embeddings:
                        if not (
                            isinstance(emb_list, list)
                            and all(isinstance(x, (int, float)) for x in emb_list)
                        ):
                            print(
                                f"Một embedding cho user_id '{user_id}' không phải là list of numbers. Cần kiểm tra file store."
                            )
                            # Có thể lọc bỏ embedding không hợp lệ này
                print(f"Đã tải {len(data)} users từ {store_path}")
                return data
        except json.JSONDecodeError:
            print(
                f"Lỗi decode JSON từ {store_path}. Trả về store rỗng."
            )
            return {}
        except Exception as e:
            print(
                f"Lỗi không xác định khi tải embedding store từ {store_path}:"
            )
            return {}
    print(f"File store {store_path} không tồn tại. Khởi tạo store rỗng.")
    return {}

def save_store():
    """Lưu dữ liệu embeddings hiện tại vào file JSON."""
    try:
        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(embeddings_data, f, indent=4)
        print(f"Dữ liệu Embeddings đã được lưu vào {store_path}")
    except Exception as e:
        print(f"Lỗi khi lưu embedding store tại {store_path}:")

def add_embedding(user_id: str, embedding: np.ndarray) -> bool:
    """
    Thêm một embedding mới vào danh sách embedding của user_id.
    Nếu user_id chưa tồn tại, tạo mới danh sách.
    """
    if not isinstance(embedding, np.ndarray):
        print(
            f"Attempted to save non-numpy array embedding for user {user_id}"
        )
        return False

    embedding_as_list = (
        embedding.tolist()
    )  # Chuyển NumPy array thành list of floats

    if user_id not in embeddings_data:
        embeddings_data[user_id] = []

    embeddings_data[user_id].append(embedding_as_list)
    save_store()
    print(
        f"Đã thêm embedding mới cho user_id: {user_id}. Tổng số embeddings: {len(embeddings_data[user_id])}"
    )
    return True

def get_embeddings_for_user(user_id: str) -> Optional[List[np.ndarray]]:
    """
    Lấy danh sách các embedding (dưới dạng NumPy array) của một user_id.
    Trả về list các NumPy array hoặc None nếu không tìm thấy user_id hoặc không có embedding.
    """
    list_of_embedding_lists = embeddings_data.get(user_id)
    if list_of_embedding_lists:
        try:
            # Chuyển mỗi list con (embedding) lại thành NumPy array
            numpy_embeddings = [
                np.array(emb_list, dtype=np.float32)
                for emb_list in list_of_embedding_lists
            ]
            print(
                f"Đã tìm thấy {len(numpy_embeddings)} embeddings cho user_id: {user_id}"
            )
            return numpy_embeddings
        except Exception as e:
            print(
                f"Lỗi khi chuyển đổi embeddings sang NumPy array cho user {user_id}:"
            )
            return None  # Hoặc một list rỗng

    print(
        f"Không tìm thấy user_id '{user_id}' hoặc không có embeddings nào trong store."
    )
    return None  # Hoặc trả về list rỗng: []

def get_all_user_ids() -> List[str]:
    """Trả về danh sách tất cả user_id đã đăng ký."""
    return list(embeddings_data.keys())

embeddings_data : Dict[str, List[List[float]]] = load_store()