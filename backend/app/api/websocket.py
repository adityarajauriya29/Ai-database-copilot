from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json

router = APIRouter()

active_connections: dict[str, WebSocket] = {}


@router.websocket("/progress/{session_id}")
async def query_progress(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        active_connections.pop(session_id, None)


async def send_progress(session_id: str, event: dict):
    ws = active_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(event)
        except Exception:
            active_connections.pop(session_id, None)
