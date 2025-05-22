from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manage import manager

router = APIRouter(prefix="/devices", tags=["devices"])

@router.websocket("/")
async def update_device(websocket: WebSocket):
    await manager.connect(websocket)
    while True:
        try:
            await websocket.receive_text() 
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            break;