"""State management for Dice Link"""

from dataclasses import dataclass, field
from typing import Any
import asyncio


@dataclass
class ConnectionState:
    """Tracks DLC connection status"""
    connected: bool = False
    client_id: str | None = None
    player_name: str | None = None
    player_id: str | None = None
    version: str | None = None


@dataclass
class RollRequest:
    """Represents an active roll request from DLC"""
    id: str
    timestamp: int
    player: dict
    roll: dict
    config: dict
    buttons: list
    raw_data: dict = field(default_factory=dict)


class AppState:
    """Global application state"""
    
    def __init__(self):
        self.connection = ConnectionState()
        self.current_roll: RollRequest | None = None
        self.dlc_websocket: Any = None  # WebSocket connection to DLC
        self.ui_websockets: set = set()  # Browser UI connections
        self.webrtc_peer_connection: Any = None  # WebRTC RTCPeerConnection from browser
        self.webrtc_data_channel: Any = None  # WebRTC data channel for messaging
        self._lock = asyncio.Lock()
    
    async def set_dlc_connected(self, client_id: str, player_name: str, player_id: str, version: str, websocket: Any):
        """Mark DLC as connected"""
        async with self._lock:
            self.connection.connected = True
            self.connection.client_id = client_id
            self.connection.player_name = player_name
            self.connection.player_id = player_id
            self.connection.version = version
            self.dlc_websocket = websocket
    
    async def set_dlc_disconnected(self):
        """Mark DLC as disconnected"""
        async with self._lock:
            self.connection.connected = False
            self.connection.client_id = None
            self.connection.player_name = None
            self.connection.player_id = None
            self.connection.version = None
            self.dlc_websocket = None
            self.current_roll = None
    
    async def set_roll_request(self, data: dict):
        """Store a new roll request"""
        async with self._lock:
            self.current_roll = RollRequest(
                id=data["id"],
                timestamp=data["timestamp"],
                player=data["player"],
                roll=data["roll"],
                config=data.get("config", {}),
                buttons=data.get("buttons", []),
                raw_data=data
            )
    
    async def clear_roll_request(self):
        """Clear the current roll request"""
        async with self._lock:
            self.current_roll = None
    
    def add_ui_websocket(self, websocket: Any):
        """Add a browser UI WebSocket connection"""
        self.ui_websockets.add(websocket)
    
    def remove_ui_websocket(self, websocket: Any):
        """Remove a browser UI WebSocket connection"""
        self.ui_websockets.discard(websocket)
    
    async def set_webrtc_peer_connection(self, pc: Any, data_channel: Any):
        """Store the WebRTC peer connection and data channel"""
        async with self._lock:
            self.webrtc_peer_connection = pc
            self.webrtc_data_channel = data_channel
    
    async def close_webrtc_connection(self):
        """Close and clean up WebRTC connection"""
        async with self._lock:
            if self.webrtc_peer_connection:
                await self.webrtc_peer_connection.close()
            self.webrtc_peer_connection = None
            self.webrtc_data_channel = None
    
    def get_status(self) -> dict:
        """Get current status for UI"""
        return {
            "connected": self.connection.connected,
            "playerName": self.connection.player_name,
            "playerId": self.connection.player_id,
            "currentRoll": self.current_roll.raw_data if self.current_roll else None
        }


# Global state instance
app_state = AppState()
