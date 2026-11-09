import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from ai_workflow.channels.websocket_manager import manager
from ai_workflow.settings import settings
from ai_workflow.storage import redis_store

router = APIRouter()

POLICY_VIOLATION = 1008


def _may_connect(session_id: str, token: str) -> bool:
    """The session must exist, and when AUTH_ENABLED the token must match."""
    session = redis_store.get_session(session_id)
    if not session:
        return False
    if settings.AUTH_ENABLED:
        return bool(session.get("token")) and secrets.compare_digest(token, session["token"])
    return True


# ============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = ""):
    """WebSocket connection for real-time agent updates"""
    if not _may_connect(session_id, token):
        await websocket.close(code=POLICY_VIOLATION)
        return

    await manager.connect(websocket, session_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to AI Orchestrator",
            "session_id": session_id
        })

        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_json({
                "type": "echo",
                "data": data
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
        logger.info("Client {} disconnected", session_id)
