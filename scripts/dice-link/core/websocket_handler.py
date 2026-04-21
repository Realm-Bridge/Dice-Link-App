"""WebSocket message handling for Dice Link"""

import json
import time
from typing import Any
from state import app_state
from config import APP_NAME, APP_VERSION
from debug import log_websocket, log_server


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
    
    # Clean up disconnected sockets
    for ws in disconnected:
        app_state.remove_ui_websocket(ws)


async def handle_dlc_message(websocket: Any, data: dict) -> dict | None:
    """
    Handle incoming message from DLC.
    Returns a response message or None.
    """
    msg_type = data.get("type")
    
    if msg_type == "connect":
        return await handle_connect(websocket, data)
    elif msg_type == "rollRequest":
        return await handle_roll_request(data)
    elif msg_type == "diceRequest":
        # Phase B: DLC sends actual dice needed after button selection
        return await handle_dice_request(data)
    elif msg_type == "playerModesUpdate":
        # Forward player modes update to UI
        return await handle_player_modes_update(data)
    elif msg_type == "requestVideoFeed":
        # Phase 3 - Video feed request from DLC
        enabled = data.get("enabled", False)
        fps = data.get("fps", 15)
        
        return {
            "type": "videoFeedStatus",
            "enabled": enabled,
            "fps": fps,
            "message": "Video streaming to DLC available via WebSocket"
        }
    else:
        return {
            "type": "error",
            "code": "INVALID_MESSAGE",
            "message": f"Unrecognized message type: {msg_type}"
        }


async def handle_connect(websocket: Any, data: dict) -> dict:
    """Handle connection handshake from DLC"""
    # Extract user info from the connect message
    user = data.get("user", {})
    user_id = user.get("id", "unknown")
    user_name = user.get("name", "Unknown Player")
    is_gm = user.get("isGM", False)
    version = data.get("version", "unknown")
    
    await app_state.set_dlc_connected(
        client_id=user_id,
        player_name=user_name,
        player_id=user_id,
        version=version,
        websocket=websocket
    )
    
    # Notify browser UI of connection
    await broadcast_to_ui({
        "type": "connectionStatus",
        "connected": True,
        "playerName": user_name,
        "playerId": user_id,
        "isGM": is_gm
    })
    
    return {
        "type": "connected",
        "version": APP_VERSION,
        "serverName": APP_NAME
    }


async def handle_roll_request(data: dict) -> None:
    """Handle incoming roll request from DLC"""
    await app_state.set_roll_request(data)
    
    # Forward roll request to browser UI
    await broadcast_to_ui({
        "type": "rollRequest",
        "data": data
    })
    
    # No direct response to DLC - results come later
    return None


async def handle_dice_request(data: dict) -> None:
    """Handle dice request from DLC (Phase B of two-phase communication)"""
    # DLC is telling us what dice to roll after button selection
    original_roll_id = data.get("originalRollId")
    roll_type = data.get("rollType")
    formula = data.get("formula")
    dice = data.get("dice", [])
    
    # Forward to browser UI to show dice entry
    await broadcast_to_ui({
        "type": "diceRequest",
        "originalRollId": original_roll_id,
        "rollType": roll_type,
        "formula": formula,
        "dice": dice
    })
    
    # No direct response to DLC
    return None


async def handle_player_modes_update(data: dict) -> None:
    """Handle player modes update from DLC"""
    # Forward player modes data to browser UI
    await broadcast_to_ui({
        "type": "playerModesUpdate",
        "globalOverride": data.get("globalOverride"),
        "players": data.get("players", [])
    })
    
    # No direct response to DLC
    return None


async def handle_dlc_disconnect():
    """Handle DLC disconnection"""
    await app_state.set_dlc_disconnected()
    
    # Notify browser UI
    await broadcast_to_ui({
        "type": "connectionStatus",
        "connected": False,
        "playerName": None,
        "playerId": None
    })


async def send_button_select(roll_id: str, button: str, config_changes: dict) -> bool:
    """Send button selection to DLC (Phase A of two-phase communication)"""
    if not app_state.dlc_websocket or not app_state.connection.connected:
        return False
    
    message = {
        "type": "buttonSelect",
        "id": roll_id,
        "button": button,
        "configChanges": config_changes
    }
    
    try:
        await app_state.dlc_websocket.send_text(json.dumps(message))
        return True
    except Exception as e:
        log_websocket(f"Error sending button select: {e}")
        return False


async def send_dice_tray_roll(formula: str, flavor: str = "Manual Dice Roll") -> bool:
    """Send a dice tray roll request to DLC for evaluation"""
    if not app_state.dlc_websocket or not app_state.connection.connected:
        log_websocket(f"send_dice_tray_roll: No DLC websocket or not connected")
        return False
    
    message = {
        "type": "diceTrayRoll",
        "formula": formula,
        "flavor": flavor
    }
    
    try:
        log_websocket(f"Sending diceTrayRoll to DLC: {message}")
        await app_state.dlc_websocket.send_text(json.dumps(message))
        return True
    except Exception as e:
        log_websocket(f"Error sending dice tray roll: {e}")
        return False


async def send_dice_result(original_roll_id: str, results: list) -> bool:
    """Send dice results to DLC (Phase B response)"""
    log_websocket(f"send_dice_result called with originalRollId={original_roll_id}, results={results}")
    
    if not app_state.dlc_websocket or not app_state.connection.connected:
        log_websocket(f"send_dice_result: No DLC websocket or not connected")
        return False
    
    message = {
        "type": "diceResult",
        "originalRollId": original_roll_id,
        "results": results
    }
    
    try:
        log_websocket(f"Sending diceResult to DLC: {message}")
        await app_state.dlc_websocket.send_text(json.dumps(message))
        await app_state.clear_roll_request()
        
        # Notify UI that roll is complete
        await broadcast_to_ui({
            "type": "rollComplete",
            "rollId": original_roll_id
        })
        
        return True
    except Exception as e:
        log_websocket(f"Error sending dice result: {e}")
        return False


async def send_roll_result(roll_id: str, button_clicked: str, config_changes: dict, results: list) -> bool:
    """Send roll result back to DLC (legacy single-phase - kept for compatibility)"""
    if not app_state.dlc_websocket or not app_state.connection.connected:
        return False
    
    message = {
        "type": "rollResult",
        "id": roll_id,
        "timestamp": int(time.time() * 1000),
        "button": button_clicked,
        "configChanges": config_changes,
        "results": results
    }
    
    try:
        await app_state.dlc_websocket.send_text(json.dumps(message))
        await app_state.clear_roll_request()
        
        # Notify UI that roll is complete
        await broadcast_to_ui({
            "type": "rollComplete",
            "rollId": roll_id
        })
        
        return True
    except Exception as e:
        log_websocket(f"Error sending roll result: {e}")
        return False


async def send_roll_cancelled(roll_id: str, reason: str = "User cancelled") -> bool:
    """Send roll cancelled message to DLC"""
    if not app_state.dlc_websocket or not app_state.connection.connected:
        return False
    
    message = {
        "type": "rollCancelled",
        "id": roll_id,
        "reason": reason
    }
    
    try:
        await app_state.dlc_websocket.send_text(json.dumps(message))
        await app_state.clear_roll_request()
        
        # Notify UI that roll is cancelled
        await broadcast_to_ui({
            "type": "rollCancelled",
            "rollId": roll_id
        })
        
        return True
    except Exception as e:
        log_websocket(f"Error sending roll cancelled: {e}")
        return False


# ============== WebRTC Helper Functions ==============

async def send_message_via_webrtc(message: dict) -> bool:
    """Send a message via WebRTC data channel if connected"""
    if not app_state.webrtc_data_channel or app_state.webrtc_data_channel.readyState != "open":
        return False
    
    try:
        app_state.webrtc_data_channel.send(json.dumps(message))
        return True
    except Exception as e:
        log_server(f"Error sending message via WebRTC: {e}")
        return False


def get_webrtc_connection_status() -> dict:
    """Get current WebRTC connection status"""
    pc_state = "disconnected"
    dc_state = "closed"
    
    if app_state.webrtc_peer_connection:
        pc_state = getattr(app_state.webrtc_peer_connection, "connectionState", "unknown")
    
    if app_state.webrtc_data_channel:
        dc_state = getattr(app_state.webrtc_data_channel, "readyState", "unknown")
    
    return {
        "peerConnectionState": pc_state,
        "dataChannelState": dc_state,
        "connected": dc_state == "open"
    }


# ============== WebRTC Handshake Debug Logging ==============

def log_handshake_step(step_num: int, step_name: str, details: str = ""):
    """Log a step in the WebRTC handshake process for debugging"""
    message = f"[WebRTC Handshake] Step {step_num}: {step_name}"
    if details:
        message += f" - {details}"
    log_server(message)

