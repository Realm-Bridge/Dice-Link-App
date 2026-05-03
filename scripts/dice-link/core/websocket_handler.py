"""WebSocket message handling for Dice Link"""

import json
from state import app_state


async def broadcast_to_ui(message: dict):
    """Send a message to all connected browser UIs"""
    if not app_state.ui_websockets:
        return

    message_str = json.dumps(message)
    disconnected = set()

    for ws in app_state.ui_websockets:
        try:
            await ws.send_text(message_str)
        except Exception:
            disconnected.add(ws)

    for ws in disconnected:
        app_state.remove_ui_websocket(ws)
