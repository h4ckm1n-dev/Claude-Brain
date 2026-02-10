"""Core Memory Service — CRUD operations and WebSocket.

Port 8100. Handles /memories/* endpoints and the /ws WebSocket.
"""

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from .base import create_app
from ..routers.memories import router as memories_router
from ..server_deps import manager

logger = logging.getLogger(__name__)

app = create_app(
    title="Memory Core",
    routers=[memories_router],
    init_qdrant=True,
    include_websocket=True,
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time memory updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.core_app:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
        log_level="info",
    )
