"""State management for Dice Link"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ConnectionState:
    """Tracks DLC connection status"""
    connected: bool = False
    client_id: str | None = None
    player_name: str | None = None
    player_id: str | None = None
    version: str | None = None


class AppState:
    """Global application state"""

    def __init__(self):
        self.connection = ConnectionState()
        self.ui_websockets: set = set()
        self.camera_stream_armed: bool = False

    def add_ui_websocket(self, websocket: Any):
        """Add a browser UI WebSocket connection"""
        self.ui_websockets.add(websocket)

    def remove_ui_websocket(self, websocket: Any):
        """Remove a browser UI WebSocket connection"""
        self.ui_websockets.discard(websocket)

    def get_status(self) -> dict:
        """Get current status for UI"""
        return {
            "connected": self.connection.connected,
            "playerName": self.connection.player_name,
            "playerId": self.connection.player_id,
            "currentRoll": None
        }


# Global state instance
app_state = AppState()
