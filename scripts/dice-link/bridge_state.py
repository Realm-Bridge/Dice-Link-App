"""Global state for DLABridge - allows Flask to communicate back through the QWebChannel bridge"""

import asyncio

# Reference to the DLABridge object, set when the viewing window is created
dla_bridge = None


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
            print(f"[BRIDGE STATE] Broadcast roll request to UI: {roll_request_data.get('id')}")
            return True
        except Exception as e:
            print(f"[BRIDGE STATE] Error broadcasting roll request to UI: {e}")
            return False
    return False


def send_roll_result_to_foundry(result_data):
    """
    Send a roll result from UI back to Foundry through the bridge.
    Called when Flask receives diceResult from the UI.
    """
    bridge = get_bridge()
    if bridge:
        try:
            bridge.sendRollResult(result_data)
            print(f"[BRIDGE STATE] Sent roll result to Foundry: {result_data.get('id')}")
            return True
        except Exception as e:
            print(f"[BRIDGE STATE] Error sending roll result to Foundry: {e}")
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
        print(f"[BRIDGE STATE] Broadcast connection status to UI: connected={connected}")
        return True
    except Exception as e:
        print(f"[BRIDGE STATE] Error broadcasting connection status to UI: {e}")
        return False

