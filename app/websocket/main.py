from fastapi import APIRouter

from app.websocket import environment
from app.websocket import devices

ws_router = APIRouter()
# api_router.include_router(rooms.router)
ws_router.include_router(devices.router)
ws_router.include_router(environment.router)

