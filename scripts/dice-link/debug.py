"""Centralized debug logging for Dice Link

All debug logging should go through this module.
Set DEBUG_ENABLED = True to enable debug output.
Set DEBUG_ENABLED = False to disable all debug output.
"""

import datetime
from pathlib import Path
from config import DEBUG

# Master debug switch - uses DEBUG from config
DEBUG_ENABLED = DEBUG

# Category-specific switches (all default to DEBUG_ENABLED)
DEBUG_UPNP = True
DEBUG_WEBSOCKET = True
DEBUG_SERVER = True
DEBUG_DRAG = True
DEBUG_CONNECTION_MONITOR = True
DEBUG_VTT = True
DEBUG_BRIDGE_STATE = True
DEBUG_STARTUP_DIALOG = True
DEBUG_DPI = True

# --- Log file ---
_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_log_file = open(_LOG_DIR / "dla.log", "a", encoding="utf-8", buffering=1)
_log_file.write(f"\n{'='*60}\n")
_log_file.write(f"Session started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
_log_file.write(f"{'='*60}\n")


def _write_log(text: str):
    """Write a timestamped entry to the log file."""
    try:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        _log_file.write(f"[{timestamp}] {text}\n")
    except Exception:
        pass


def log(category: str, message: str):
    """Log a debug message if debugging is enabled."""
    if not DEBUG_ENABLED:
        return
    line = f"[{category} DEBUG] {message}"
    print(line)
    _write_log(line)


def log_upnp(message: str):
    """Log UPnP-related debug messages."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        line = f"[UPnP] {message}"
        print(line)
        _write_log(line)


def log_websocket(message: str):
    """Log WebSocket-related debug messages."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        line = f"[WebSocket DEBUG] {message}"
        print(line)
        _write_log(line)


def log_server(message: str):
    """Log server-related debug messages."""
    if DEBUG_ENABLED and DEBUG_SERVER:
        line = f"[Server DEBUG] {message}"
        print(line)
        _write_log(line)


def log_dlc_connection(client_host: str, client_port: int, headers: dict):
    """Log DLC connection attempt details."""
    if not (DEBUG_ENABLED and DEBUG_WEBSOCKET):
        return
    lines = [
        f"[WebSocket DEBUG] /ws/dlc connection attempt received",
        f"[WebSocket DEBUG] Client address: {client_host}:{client_port}",
        f"[WebSocket DEBUG] Headers: {headers}"
    ]
    for line in lines:
        print(line)
        _write_log(line)


def log_dlc_accepted():
    """Log DLC connection accepted."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        line = "[WebSocket DEBUG] WebSocket connection ACCEPTED for /ws/dlc"
        print(line)
        _write_log(line)


def log_dlc_message(data: str):
    """Log DLC message received."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        truncated = data[:200] + "..." if len(data) > 200 else data
        line = f"[WebSocket DEBUG] Received message from DLC: {truncated}"
        print(line)
        _write_log(line)


def log_dlc_response(response: str):
    """Log DLC response sent."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        truncated = response[:200] + "..." if len(response) > 200 else response
        line = f"[WebSocket DEBUG] Sending response to DLC: {truncated}"
        print(line)
        _write_log(line)


def log_dlc_disconnect(clean: bool = True, error: str = None):
    """Log DLC disconnection."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        if clean:
            line = "[WebSocket DEBUG] WebSocket disconnected (clean disconnect)"
        else:
            line = f"[WebSocket DEBUG] WebSocket error: {error}"
        print(line)
        _write_log(line)


def log_connection_monitor(message: str):
    """Log connection monitoring debug messages."""
    if DEBUG_ENABLED and DEBUG_CONNECTION_MONITOR:
        line = f"[Connection Monitor DEBUG] {message}"
        print(line)
        _write_log(line)


def log_upnp_device(device_name: str, device_type: str = "unknown"):
    """Log UPnP device discovery."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        lines = [
            f"[UPnP DEBUG] Checking device: {device_name}",
            f"[UPnP DEBUG] Device type: {device_type}"
        ]
        for line in lines:
            print(line)
            _write_log(line)


def log_upnp_services(services: list):
    """Log available UPnP services."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        line = f"[UPnP DEBUG] Available services: {services}"
        print(line)
        _write_log(line)


def log_upnp_service_detail(service_id: str, service_type: str = None, actions: list = None, error: str = None):
    """Log UPnP service details."""
    if not (DEBUG_ENABLED and DEBUG_UPNP):
        return
    lines = [f"[UPnP DEBUG] Examining service: {service_id}"]
    if service_type:
        lines.append(f"[UPnP DEBUG] Service type string: {service_type}")
    if actions:
        lines.append(f"[UPnP DEBUG] Service actions: {actions}")
    if error:
        lines.append(f"[UPnP DEBUG] Error accessing service: {error}")
    for line in lines:
        print(line)
        _write_log(line)


def log_upnp_error(context: str, error: str, traceback: str = None):
    """Log UPnP errors with optional traceback."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        lines = [f"[UPnP DEBUG] Error {context}: {error}"]
        if traceback:
            lines.append(f"[UPnP DEBUG] Traceback: {traceback}")
        for line in lines:
            print(line)
            _write_log(line)


def log_startup(host: str, port: int):
    """Log server startup configuration."""
    if DEBUG_ENABLED and DEBUG_SERVER:
        lines = [
            f"[Server DEBUG] WEBSOCKET_HOST configured as: {host}",
            f"[Server DEBUG] WEBSOCKET_PORT configured as: {port}",
            f"[Server DEBUG] Waiting for connections on /ws/dlc endpoint..."
        ]
        for line in lines:
            print(line)
            _write_log(line)


def log_drag(message: str):
    """Log drag-related debug messages."""
    if DEBUG_ENABLED and DEBUG_DRAG:
        line = f"[Drag DEBUG] {message}"
        print(line)
        _write_log(line)


def log_drag_start(global_pos_float, drag_position, window_pos):
    """Log drag start details."""
    if not (DEBUG_ENABLED and DEBUG_DRAG):
        return
    lines = [
        "[Drag DEBUG] === DRAG START ===",
        f"[Drag DEBUG] globalPosition (float): {global_pos_float.x()}, {global_pos_float.y()}",
        f"[Drag DEBUG] drag_position stored: {drag_position.x()}, {drag_position.y()}",
        f"[Drag DEBUG] window pos at start: {window_pos.x()}, {window_pos.y()}"
    ]
    for line in lines:
        print(line)
        _write_log(line)


def log_drag_move(global_pos_float, global_pos_int, drag_position, calculated_pos, current_window_pos):
    """Log drag move details."""
    if not (DEBUG_ENABLED and DEBUG_DRAG):
        return
    lines = [
        f"[Drag DEBUG] globalPosition (float): {global_pos_float.x()}, {global_pos_float.y()}",
        f"[Drag DEBUG] globalPosition (int):   {global_pos_int.x()}, {global_pos_int.y()}",
        f"[Drag DEBUG] drag_position: {drag_position.x()}, {drag_position.y()}",
        f"[Drag DEBUG] calculated move pos: {calculated_pos.x()}, {calculated_pos.y()}",
        f"[Drag DEBUG] current window pos: {current_window_pos.x()}, {current_window_pos.y()}",
        "---"
    ]
    for line in lines:
        print(line)
        _write_log(line)


def log_drag_end():
    """Log drag end."""
    if DEBUG_ENABLED and DEBUG_DRAG:
        line = "[Drag DEBUG] === DRAG END ==="
        print(line)
        _write_log(line)


def log_vtt(message: str):
    """Log VTT-related debug messages."""
    if DEBUG_ENABLED and DEBUG_VTT:
        line = f"[VTT DEBUG] {message}"
        print(line)
        _write_log(line)


def log_bridge_state(message: str):
    """Log bridge state messages."""
    if DEBUG_ENABLED and DEBUG_BRIDGE_STATE:
        line = f"[Bridge State] {message}"
        print(line)
        _write_log(line)


def log_startup_dialog(message: str):
    """Log startup dialog messages."""
    if DEBUG_ENABLED and DEBUG_STARTUP_DIALOG:
        line = f"[Startup Dialog] {message}"
        print(line)
        _write_log(line)


def log_dpi(message: str):
    """Log DPI scaling messages."""
    if DEBUG_ENABLED and DEBUG_DPI:
        line = f"[DPI] {message}"
        print(line)
        _write_log(line)
