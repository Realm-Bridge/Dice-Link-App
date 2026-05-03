"""Global state for DLABridge - allows Flask to communicate back through the QWebChannel bridge"""

import asyncio
import json
from debug import log_bridge_state

# Reference to the DLABridge object, set when the viewing window is created
dla_bridge = None

# Global state for player name
current_player_name = None


def set_bridge(bridge):
    """Store reference to DLABridge"""
    global dla_bridge
    dla_bridge = bridge


def get_bridge():
    """Get reference to DLABridge"""
    return dla_bridge


def send_roll_request_to_ui(roll_request_data):
    """
    Send a roll request from Foundry to the UI controls window.
    Called when DLABridge receives receiveRollRequest from Foundry.
    """
    if dla_bridge:
        roll_request_data['type'] = 'rollRequest'

        # Broadcast to UI via WebSocket
        try:
            from state import app_state
            # Use asyncio to run the async broadcast function from a sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            from core.websocket_handler import broadcast_to_ui
            loop.run_until_complete(broadcast_to_ui(roll_request_data))
            log_bridge_state(f"Broadcast roll request to UI: {roll_request_data.get('id')}")
            return True
        except Exception as e:
            log_bridge_state(f"Error broadcasting roll request to UI: {e}")
            return False
    return False


def send_dice_result_to_foundry(result_data):
    """
    Send dice result from UI back to Foundry through the bridge.
    Called when Flask receives diceResult from the UI.
    Uses diceResultReady signal (not rollResultReady) as DLC expects.
    """
    bridge = get_bridge()
    if bridge:
        try:
            bridge.sendDiceResult(result_data)
            log_bridge_state(f"Sent dice result to Foundry: {result_data.get('id')}")
            return True
        except Exception as e:
            log_bridge_state(f"Error sending dice result to Foundry: {e}")
            return False
    return False


def send_dice_tray_roll_to_foundry(formula, flavor):
    """
    Send dice tray roll from UI to Foundry through the bridge.
    Called when Flask receives diceTrayRoll from the UI.
    Uses diceTrayRollReady signal as DLC expects.
    """
    bridge = get_bridge()
    if bridge:
        try:
            dice_tray_data = {
                "type": "diceTrayRoll",
                "formula": formula,
                "flavor": flavor
            }
            bridge.sendDiceTrayRoll(dice_tray_data)
            log_bridge_state(f"Sent dice tray roll to Foundry: formula={formula}, flavor={flavor}")
            return True
        except Exception as e:
            log_bridge_state(f"Error sending dice tray roll to Foundry: {e}")
            return False
    return False


def send_connection_status_to_ui(connected, player_name=None):
    """
    Send connection status to the UI controls window.
    Called when DLC connects or disconnects via QWebChannel.
    """
    try:
        from core.websocket_handler import broadcast_to_ui

        status_message = {
            'type': 'connectionStatus',
            'connected': connected,
            'playerName': player_name or 'Foundry VTT'
        }

        # Use asyncio to run the async broadcast function from a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(broadcast_to_ui(status_message))
        log_bridge_state(f"Broadcast connection status to UI: connected={connected}, player={player_name}")
        return True
    except Exception as e:
        log_bridge_state(f"Error broadcasting connection status to UI: {e}")
        return False


def update_connection_player_name(player_name):
    """Update the stored player name from player modes data."""
    global current_player_name
    current_player_name = player_name
    log_bridge_state(f"Updated player name: {player_name}")


def get_current_player_name():
    """Get the currently stored player name."""
    return current_player_name


def send_player_modes_to_ui(player_modes_data):
    """
    Send player modes data from DLC to the UI controls window.
    Called when DLC broadcasts player modes update via QWebChannel.

    Converts DLC data format (object with numeric keys) to UI expected format (array).
    """
    try:
        from core.websocket_handler import broadcast_to_ui

        # Convert player modes data from DLC format to UI format
        # DLC format: {"0": {"id": "...", "name": "...", "mode": "..."}, ...}
        # UI format: [{"id": "...", "name": "...", "mode": "..."}, ...]
        players_array = []
        if isinstance(player_modes_data, dict):
            for key, player_data in player_modes_data.items():
                if isinstance(player_data, dict):
                    players_array.append(player_data)

        message = {
            'type': 'playerModesUpdate',
            'players': players_array
        }

        # Use asyncio to run the async broadcast function from a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(broadcast_to_ui(message))
        log_bridge_state(f"Broadcast player modes to UI: {len(players_array)} players")
        return True
    except Exception as e:
        log_bridge_state(f"Error broadcasting player modes to UI: {e}")
        return False


def send_camera_frame_to_dlc(frame_b64: str):
    """Send a single camera frame to DLC via the bridge."""
    bridge = get_bridge()
    if bridge:
        try:
            bridge.sendCameraFrame(frame_b64)
            return True
        except Exception as e:
            log_bridge_state(f"Error sending camera frame to DLC: {e}")
            return False
    return False


def send_camera_stream_end_to_dlc():
    """Signal DLC that the camera stream has ended."""
    bridge = get_bridge()
    if bridge:
        try:
            bridge.sendCameraStreamEnd()
            return True
        except Exception as e:
            log_bridge_state(f"Error sending camera stream end to DLC: {e}")
            return False
    return False


def send_button_select_to_dlc(button_data):
    """
    Send button selection from UI to DLC via the bridge.
    Called when user clicks a button in the controls window.
    """
    bridge = get_bridge()
    if bridge:
        try:
            bridge.receiveButtonSelect(json.dumps(button_data))
            log_bridge_state(f"Sent button select to DLC: {button_data.get('button')}")
            return True
        except Exception as e:
            log_bridge_state(f"Error sending button select to DLC: {e}")
            return False
    return False


def send_dice_request_to_ui(dice_request_data):
    """
    Send a dice request from DLC to the UI controls window.
    Called when DLABridge receives receiveDiceRequest from DLC.
    This tells the UI to close the roll request window and show the dice rolling screen.
    """
    try:
        from core.websocket_handler import broadcast_to_ui

        dice_request_data['type'] = 'diceRequest'

        # Use asyncio to run the async broadcast function from a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(broadcast_to_ui(dice_request_data))
        log_bridge_state(f"Broadcast dice request to UI: {dice_request_data.get('id')}")
        return True
    except Exception as e:
        log_bridge_state(f"Error broadcasting dice request to UI: {e}")
        return False
