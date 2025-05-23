# import sentry_sdk
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware

from app.utils import aio, send_queue
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
# if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
#     sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    worker_task = asyncio.create_task(aio_worker())
    print("AIO Worker started")
    yield
    # Shutdown logic (nếu cần)
    worker_task.cancel()
    print("AIO Worker stopped")
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