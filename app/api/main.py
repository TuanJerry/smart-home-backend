from fastapi import APIRouter

from app.api.routes import rooms, devices, environment
# from app.core.config import settings

api_router = APIRouter()
api_router.include_router(rooms.router)
api_router.include_router(devices.router)
api_router.include_router(environment.router)

# if settings.ENVIRONMENT == "local":
#     api_router.include_router(private.router)
