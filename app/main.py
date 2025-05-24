# import sentry_sdk
import torch
import asyncio
from contextlib import asynccontextmanager
from transformers import pipeline, AutoTokenizer, AutoModel

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware

from app.utils import aio, send_queue, model_ready, AImodel
from app.api.main import api_router
from app.core.config import settings
from app.websocket.main import ws_router


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"

async def aio_worker():
    while True:
        device_type, value = await send_queue.get()
        try:
            await asyncio.to_thread(aio.send, device_type, value)
            print(f"[AIO] Sent {device_type}: {value}")
        except Exception as e:
            print(f"[AIO ERROR] Failed to send {device_type}: {e}")
        finally:
            send_queue.task_done()

async def model_worker():
    device = 0 if torch.cuda.is_available() else -1
    try:
        print(f"📦 Đang load ASR model lên {'GPU' if device == 0 else 'CPU'}...")
        AImodel.asr_pipeline = await asyncio.to_thread(
            pipeline,
            "automatic-speech-recognition",
            model="tuan8p/whisper-small-vi",
            device=device
        )
        print("✅ ASR model đã sẵn sàng.")

        print(f"📦 Đang load NLP model lên {'GPU' if device == 0 else 'CPU'}...")
        AImodel.tokenizer = await asyncio.to_thread(
            AutoTokenizer.from_pretrained,
            "vinai/phobert-base-v2",
            trust_remote_code=True
        )
        AImodel.nlp_model = await asyncio.to_thread(
            AutoModel.from_pretrained,
            "vinai/phobert-base-v2",
            trust_remote_code=True,
            use_safetensors=True
        )
        print("✅ NLP model đã sẵn sàng.")
        model_ready.set()  # Đánh dấu mô hình đã sẵn sàng
    except Exception as e:
        print(f"[MODEL ERROR] ❌ Lỗi khi tải mô hình: {e}")
        raise e

# if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
#     sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    worker_task = asyncio.create_task(aio_worker())
    model_task = asyncio.create_task(model_worker())
    print("AIO Worker started")
    print("Model loading successfully")
    yield
    # Shutdown logic (nếu cần)
    worker_task.cancel()
    model_task.cancel()
    print("AIO Worker stopped")
    print("Stop model loading")
    print("Application stopped")


app = FastAPI(
    title = settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function = custom_generate_unique_id,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix="/ws", tags=["websocket"])