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
DEBUG_SERVER = True
DEBUG_DRAG = False
DEBUG_CONNECTION_MONITOR = True
DEBUG_VTT = True
DEBUG_BRIDGE_STATE = True
DEBUG_STARTUP_DIALOG = False
DEBUG_DPI = False
DEBUG_SNAP = False

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


def log_server(message: str):
    """Log server-related debug messages."""
    if DEBUG_ENABLED and DEBUG_SERVER:
        line = f"[Server DEBUG] {message}"
        print(line)
        _write_log(line)


def log_connection_monitor(message: str):
    """Log connection monitoring debug messages."""
    if DEBUG_ENABLED and DEBUG_CONNECTION_MONITOR:
        line = f"[Connection Monitor DEBUG] {message}"
        print(line)
        _write_log(line)


def log_startup(host: str, port: int):
    """Log server startup configuration."""
    if DEBUG_ENABLED and DEBUG_SERVER:
        lines = [
            f"[Server DEBUG] WEBSOCKET_HOST configured as: {host}",
            f"[Server DEBUG] WEBSOCKET_PORT configured as: {port}",
            f"[Server DEBUG] Ready for QWebChannel connections from embedded browser..."
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


def log_snap(message: str):
    """Log Windows snap/docking native event messages."""
    if DEBUG_ENABLED and DEBUG_SNAP:
        line = f"[Snap] {message}"
        print(line)
        _write_log(line)


def log_flicker():
    """Log a user-reported flicker marker. Always written regardless of debug settings."""
    line = "[FLICKER REPORTED] <<<<<<<<<<<<<<<<<<<<<<<<<<"
    print(line)
    _write_log(line)
