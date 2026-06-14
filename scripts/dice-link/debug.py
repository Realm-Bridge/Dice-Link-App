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
DEBUG_CHAT_LOG = True
DEBUG_STORAGE = True
DEBUG_CAMERA_MOTION = True
DEBUG_CAMERA_CAPTURE = True

# --- Log file ---
# Live log: logs/dla.log — archived to dla_archive.log on every startup; contains only the current session.
# Archive:  logs/dla_archive.log — single permanent file; all previous sessions appended here.
_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_PATH = _LOG_DIR / "dla.log"
_ARCHIVE_PATH = _LOG_DIR / "dla_archive.log"

if _LOG_PATH.exists():
    _existing = _LOG_PATH.read_text(encoding="utf-8", errors="replace")
    if _existing.strip():
        with open(_ARCHIVE_PATH, "a", encoding="utf-8") as _arc:
            _arc.write(_existing)
    _LOG_PATH.write_text("", encoding="utf-8")

_log_file = open(_LOG_PATH, "a", encoding="utf-8", buffering=1)
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



def log_chat_log(message: str):
    """Log chat log pipeline events — DLC payload receipt, CSS counts, message counts."""
    if DEBUG_ENABLED and DEBUG_CHAT_LOG:
        line = f"[Chat Log] {message}"
        print(line)
        _write_log(line)


def log_storage(message: str):
    """Log dice roll storage events — database init, session start, roll saves."""
    if DEBUG_ENABLED and DEBUG_STORAGE:
        line = f"[Storage] {message}"
        print(line)
        _write_log(line)


def log_camera_motion(message: str):
    """Log motion detection events — pixel counts, thresholds, and state changes."""
    if DEBUG_ENABLED and DEBUG_CAMERA_MOTION:
        line = f"[Camera Motion] {message}"
        print(line)
        _write_log(line)


def log_camera_capture(message: str):
    """Log capture loop events — read latency, ret value, frame content."""
    if DEBUG_ENABLED and DEBUG_CAMERA_CAPTURE:
        line = f"[Camera Capture] {message}"
        print(line)
        _write_log(line)
