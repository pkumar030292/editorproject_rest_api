from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from utils import whiteboard_core
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for connection in self.active_connections:
            await connection.send_text(data)

manager = ConnectionManager()

# Whiteboard page
@router.get("/whiteboard")
async def whiteboard_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# WebSocket for strokes
@router.websocket("/whiteboard/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            whiteboard_core.save_stroke(message)
            await manager.broadcast(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Snapshot saving
@router.post("/whiteboard/snapshot")
async def save_snapshot(snapshot: dict = Body(...)):
    filename = whiteboard_core.save_snapshot(snapshot["snapshot"])
    return JSONResponse({"filename": filename})
