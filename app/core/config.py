# import secrets
# import warnings

from pathlib import Path
from pydantic import (
    PostgresDsn,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from Adafruit_IO import Client

class Settings(BaseSettings):
    # Cấu hình dùng để đọc file env của chương trình
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/v1"
    # SECRET_KEY: str = secrets.token_urlsafe(32)
    # # 60 minutes * 24 hours * 8 days = 8 days
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    PROJECT_NAME: str = ""
    # SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # Setup các thông số account của Postgres để return Connection String kết nối database
    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
    
    ADAFRUIT_IO_USERNAME: str = ""
    ADAFRUIT_IO_KEY: str = ""
    # Setup các thông số account của Adafruit IO để return Client kết nối với remote server
    @computed_field  # type: ignore[prop-decorator]
    @property
    def ADAFRUIT_IO_CLIENT(self) -> Client:
        return Client(self.ADAFRUIT_IO_USERNAME, self.ADAFRUIT_IO_KEY)

    # SMTP_TLS: bool = True
    # SMTP_SSL: bool = False
    # SMTP_PORT: int = 587
    # SMTP_HOST: str | None = None
    # SMTP_USER: str | None = None
    # SMTP_PASSWORD: str | None = None
    # EMAILS_FROM_EMAIL: EmailStr | None = None
    # EMAILS_FROM_NAME: EmailStr | None = None

    # @model_validator(mode="after")
    # def _set_default_emails_from(self) -> Self:
    #     if not self.EMAILS_FROM_NAME:
    #         self.EMAILS_FROM_NAME = self.PROJECT_NAME
    #     return self

    # EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    # @computed_field  # type: ignore[prop-decorator]
    # @property
    # def emails_enabled(self) -> bool:
    #     return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    # EMAIL_TEST_USER: EmailStr = "test@example.com"
    # FIRST_SUPERUSER: EmailStr
    # FIRST_SUPERUSER_PASSWORD: str

    # def _check_default_secret(self, var_name: str, value: str | None) -> None:
    #     if value == "changethis":
    #         message = (
    #             f'The value of {var_name} is "changethis", '
    #             "for security, please change it, at least for deployments."
    #         )
    #         if self.ENVIRONMENT == "local":
    #             warnings.warn(message, stacklevel=1)
    #         else:
    #             raise ValueError(message)

    # @model_validator(mode="after")
    # def _enforce_non_default_secrets(self) -> Self:
    #     self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
    #     self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
    #     self._check_default_secret(
    #         "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
    #     )

    #     return self

    # Setup các thông số cho model Hình ảnh nhận diện khuôn mặt (Camera)
    BASE_DIR : Path = Path(__file__).resolve().parent.parent.parent
    # Thông số đánh giá độ chính xác của nhân diện khuôn mặt
    OPTIMAL_THRESHOLD : float = 1.2 
    CONFIDENCE_VERIFICATION_THRESHOLD : float = 0.6
    # Thông tin về model Siamese branch
    MODEL_NAME : str = "siamese_branch_model_best.h5"  # Tên file model của bạn
    MODEL_PATH : Path = BASE_DIR / "models_AI" / MODEL_NAME
    # Kích thước input mà mô hình Siamese branch mong đợi
    MODEL_INPUT_SHAPE : tuple[int, int, int] = (100, 100, 3)  # (Cao, Rộng, Kênh)
    # Đường dẫn đến thư mục chứa ảnh đã được mã hóa
    EMBEDDINGS_STORE_DIR : Path = BASE_DIR / "app" / "embeddings"
    EMBEDDINGS_STORE_FILE_NAME : Path = "embeddings_store.json"
    EMBEDDINGS_STORE_PATH : Path = EMBEDDINGS_STORE_DIR / EMBEDDINGS_STORE_FILE_NAME

settings = Settings() 
