# backend_face_id/app/services/face_verification_service.py
import tensorflow as tf

# from tensorflow.keras.models import load_model # Không cần nữa nếu chỉ load weights
from keras.models import Model
from keras.layers import Input, Conv2D, MaxPooling2D, Flatten, Dense
import numpy as np
from PIL import Image
import io
from pathlib import Path
from typing import Optional

from app.core.config import settings

# (Logger setup - ví dụ)
import logging

logger = logging.getLogger(__name__)
# Bạn nên cấu hình logger này ở đâu đó trong ứng dụng, ví dụ trong app/main.py hoặc app/core/config.py
# Ví dụ cấu hình cơ bản:
# logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(module)s: %(message)s')

from pillow_heif import register_heif_opener

register_heif_opener()


# --- Hàm tạo kiến trúc backbone (PHẢI GIỐNG HỆT như lúc huấn luyện) ---
def create_siamese_backbone_service(
    input_shape,
):  # Đổi tên một chút để tránh trùng nếu import từ nơi khác
    """
    Tạo lại kiến trúc CNN cơ sở cho một nhánh của Siamese Network.
    Tất cả các lớp Conv và Dense đều sử dụng hàm kích hoạt ReLU.
    """
    inputs = Input(shape=input_shape, name="backbone_input")
    x = Conv2D(
        filters=32,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv1_1",
    )(inputs)
    x = Conv2D(
        filters=32,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv1_2",
    )(x)
    x = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), padding="valid", name="pool1")(
        x
    )  # 100->50

    x = Conv2D(
        filters=64,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv2_1",
    )(x)
    x = Conv2D(
        filters=128,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv2_2",
    )(x)
    x = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), padding="valid", name="pool2")(
        x
    )  # 50->25

    x = Conv2D(
        filters=512,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv3_1",
    )(x)
    x = Conv2D(
        filters=512,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv3_2",
    )(x)
    x = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), padding="valid", name="pool3")(
        x
    )  # 25->12 (do 25/2=12.5, floor)

    x = Conv2D(
        filters=1024,
        kernel_size=(3, 3),
        strides=(1, 1),
        padding="same",
        activation="relu",
        name="conv4",
    )(x)
    # Output shape sau conv4: (None, 12, 12, 1024) nếu input là 100x100

    x = Flatten(name="flatten")(x)
    x = Dense(units=400, activation="relu", name="fc1")(x)
    x = Dense(units=400, activation="relu", name="fc2")(x)
    embedding_output = Dense(units=400, activation="relu", name="fc3_embedding")(x)

    backbone_model = Model(
        inputs=inputs, outputs=embedding_output, name="siamese_backbone_recreated"
    )
    return backbone_model


class FaceVerificationService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FaceVerificationService, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    def __init__(self):
        if hasattr(self, "model_loaded") and self.model_loaded:
            return

        self.model_path_weights = (
            settings.MODEL_PATH  # Đây là đường dẫn đến file .h5 chứa trọng số
        )
        self.model_input_shape = settings.MODEL_INPUT_SHAPE  # Ví dụ: (100, 100, 3)
        self.target_height = self.model_input_shape[0]
        self.target_width = self.model_input_shape[1]
        self.num_channels = self.model_input_shape[2]

        self.model: Optional[Model] = None  # Khai báo kiểu cho model
        self.model_loaded = False
        self._load_model_and_weights()

    def _load_model_and_weights(self):
        logger.info(
            f"Attempting to recreate architecture and load weights from: {self.model_path_weights}"
        )
        if not self.model_path_weights.exists():
            logger.critical(
                f"Model weights file not found at {self.model_path_weights}"
            )
            return

        try:
            # 1. Tạo lại kiến trúc mô hình
            logger.info(
                f"Recreating Siamese backbone architecture with input shape: {self.model_input_shape}"
            )
            self.model = create_siamese_backbone_service(self.model_input_shape)

            # 2. Tải trọng số vào kiến trúc đã tạo
            logger.info(f"Loading weights from {self.model_path_weights}...")
            self.model.load_weights(
                str(self.model_path_weights)
            )  # load_weights nhận string path

            logger.info(
                "Model weights loaded successfully into recreated architecture."
            )
            self.model_loaded = True
            # In summary để kiểm tra (chỉ nên dùng khi debug, có thể bỏ trong production)
            # self.model.summary(print_fn=logger.info)

        except Exception as e:
            logger.exception(
                f"Critical error recreating architecture or loading weights from {self.model_path_weights}:"
            )
            # self.model_loaded vẫn là False

    def _preprocess_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        if not image_bytes:
            logger.warning("preprocess_image received empty image_bytes.")
            return None
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert("RGB")
            # Sử dụng self.target_width, self.target_height đã lấy từ MODEL_INPUT_SHAPE
            image = image.resize((self.target_width, self.target_height))
            img_array = np.array(image, dtype=np.float32)
            img_array = img_array / 255.0
            img_array_expanded = np.expand_dims(img_array, axis=0)

            expected_shape = (
                1,
                self.target_height,
                self.target_width,
                self.num_channels,
            )
            if img_array_expanded.shape != expected_shape:
                logger.error(
                    f"Preprocessed image shape mismatch. Expected {expected_shape}, got {img_array_expanded.shape}"
                )
                return None
            return img_array_expanded
        except Exception as e:
            logger.exception(f"Error preprocessing image:")
            return None

    def get_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        if not self.model_loaded or self.model is None:
            logger.error(
                "Model not loaded or not an instance of Model. Cannot get embedding."
            )
            return None

        preprocessed_img = self._preprocess_image(image_bytes)
        if preprocessed_img is None:
            logger.error("Image preprocessing failed. Cannot get embedding.")
            return None

        try:
            embedding = self.model.predict(preprocessed_img, verbose=0)
            return embedding.squeeze()
        except Exception as e:
            logger.exception(f"Error during model prediction for embedding:")
            return None
        
face_service = FaceVerificationService()

# # --- Phần kiểm tra nhanh (chỉ chạy khi thực thi file này trực tiếp) ---
# if __name__ == "__main__":
#     import sys

#     # (Phần sys.path.insert như cũ)
#     # ... (Phần kiểm tra như cũ, nhưng nó sẽ gọi _load_model_and_weights) ...

#     # Cấu hình logging cơ bản để thấy output của logger khi chạy độc lập
#     logging.basicConfig(
#         level=logging.INFO,
#         format="[%(asctime)s] %(levelname)s: %(module)s - %(funcName)s: %(message)s",
#     )

#     SERVICE_FILE_PATH = Path(__file__).resolve()
#     PROJECT_ROOT = SERVICE_FILE_PATH.parent.parent.parent

#     if str(PROJECT_ROOT) not in sys.path:
#         sys.path.insert(0, str(PROJECT_ROOT))
#         logger.info(f"Đã thêm '{PROJECT_ROOT}' vào sys.path cho import")

#     try:
#         from app.core.config import (
#             MODEL_PATH as test_model_path_weights,
#             MODEL_INPUT_SHAPE as test_model_input_shape_cfg,
#         )

#         logger.info(
#             f"Đường dẫn file trọng số model sẽ được service sử dụng (từ config): {test_model_path_weights}"
#         )
#         logger.info(f"Input shape của model (từ config): {test_model_input_shape_cfg}")
#     except ModuleNotFoundError:
#         logger.error(
#             "LỖI: Không thể import 'app.core.config'. Kiểm tra lại sys.path và cấu trúc thư mục."
#         )
#         logger.info(f"sys.path hiện tại: {sys.path}")
#         exit()
#     except ImportError as ie:
#         logger.error(f"LỖI: Có vấn đề khi import từ 'app.core.config': {ie}")
#         logger.info(f"sys.path hiện tại: {sys.path}")
#         exit()

#     if not test_model_path_weights.exists():
#         logger.warning(
#             f"CẢNH BÁO KIỂM TRA: File trọng số model tại '{test_model_path_weights}' không tồn tại."
#         )
#     else:
#         logger.info(
#             f"File trọng số model tại '{test_model_path_weights}' được tìm thấy."
#         )

#     face_service = FaceVerificationService()

#     if face_service.model_loaded and face_service.model is not None:
#         logger.info("Service đã khởi tạo và model (kiến trúc + trọng số) đã được tải.")

#         dummy_image_array = np.random.randint(
#             0, 256, size=test_model_input_shape_cfg, dtype=np.uint8
#         )
#         dummy_pil_image = Image.fromarray(dummy_image_array)

#         img_byte_arr = io.BytesIO()
#         dummy_pil_image.save(img_byte_arr, format="PNG")
#         dummy_image_bytes = img_byte_arr.getvalue()

#         logger.info(
#             f"Thử lấy embedding cho một ảnh dummy {test_model_input_shape_cfg}..."
#         )
#         embedding = face_service.get_embedding(dummy_image_bytes)
#         if embedding is not None:
#             logger.info(f"Embedding thu được có shape: {embedding.shape}")
#             logger.info(f"Một vài giá trị embedding đầu tiên: {embedding[:5]}")
#         else:
#             logger.error("Không lấy được embedding cho ảnh dummy.")
#     else:
#         logger.error(
#             "Service khởi tạo nhưng model KHÔNG được tải. Kiểm tra lỗi ở trên."
#         )

#     logger.info("--- Kết thúc kiểm tra FaceVerificationService ---")
