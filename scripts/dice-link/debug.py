"""Centralized debug logging for Dice Link

All debug logging should go through this module.
Set DEBUG_ENABLED = True to enable debug output.
Set DEBUG_ENABLED = False to disable all debug output.
"""

from config import DEBUG

# Master debug switch - uses DEBUG from config
DEBUG_ENABLED = DEBUG

# Category-specific switches (all default to DEBUG_ENABLED)
DEBUG_UPNP = True
DEBUG_WEBSOCKET = True
DEBUG_SERVER = True


def log(category: str, message: str):
    """Log a debug message if debugging is enabled."""
    if not DEBUG_ENABLED:
        return
    print(f"[{category} DEBUG] {message}")


def log_upnp(message: str):
    """Log UPnP-related debug messages."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        print(f"[UPnP DEBUG] {message}")


def log_websocket(message: str):
    """Log WebSocket-related debug messages."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        print(f"[WebSocket DEBUG] {message}")


def log_server(message: str):
    """Log server-related debug messages."""
    if DEBUG_ENABLED and DEBUG_SERVER:
        print(f"[Server DEBUG] {message}")


def log_dlc_connection(client_host: str, client_port: int, headers: dict):
    """Log DLC connection attempt details."""
    if not (DEBUG_ENABLED and DEBUG_WEBSOCKET):
        return
    print(f"[WebSocket DEBUG] /ws/dlc connection attempt received")
    print(f"[WebSocket DEBUG] Client address: {client_host}:{client_port}")
    print(f"[WebSocket DEBUG] Headers: {headers}")


def log_dlc_accepted():
    """Log DLC connection accepted."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        print(f"[WebSocket DEBUG] WebSocket connection ACCEPTED for /ws/dlc")


def log_dlc_message(data: str):
    """Log DLC message received."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        truncated = data[:200] + "..." if len(data) > 200 else data
        print(f"[WebSocket DEBUG] Received message from DLC: {truncated}")


def log_dlc_response(response: str):
    """Log DLC response sent."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        truncated = response[:200] + "..." if len(response) > 200 else response
        print(f"[WebSocket DEBUG] Sending response to DLC: {truncated}")


def log_dlc_disconnect(clean: bool = True, error: str = None):
    """Log DLC disconnection."""
    if DEBUG_ENABLED and DEBUG_WEBSOCKET:
        if clean:
            print(f"[WebSocket DEBUG] WebSocket disconnected (clean disconnect)")
        else:
            print(f"[WebSocket DEBUG] WebSocket error: {error}")


def log_upnp_device(device_name: str, device_type: str = "unknown"):
    """Log UPnP device discovery."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        print(f"[UPnP DEBUG] Checking device: {device_name}")
        print(f"[UPnP DEBUG] Device type: {device_type}")


def log_upnp_services(services: list):
    """Log available UPnP services."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        print(f"[UPnP DEBUG] Available services: {services}")


def log_upnp_service_detail(service_id: str, service_type: str = None, actions: list = None, error: str = None):
    """Log UPnP service details."""
    if not (DEBUG_ENABLED and DEBUG_UPNP):
        return
    print(f"[UPnP DEBUG] Examining service: {service_id}")
    if service_type:
        print(f"[UPnP DEBUG] Service type string: {service_type}")
    if actions:
        print(f"[UPnP DEBUG] Service actions: {actions}")
    if error:
        print(f"[UPnP DEBUG] Error accessing service: {error}")


def log_upnp_error(context: str, error: str, traceback: str = None):
    """Log UPnP errors with optional traceback."""
    if DEBUG_ENABLED and DEBUG_UPNP:
        print(f"[UPnP DEBUG] Error {context}: {error}")
        if traceback:
            print(f"[UPnP DEBUG] Traceback: {traceback}")


def log_startup(host: str, port: int):
    """Log server startup configuration."""
    if DEBUG_ENABLED and DEBUG_SERVER:
        print(f"[Server DEBUG] WEBSOCKET_HOST configured as: {host}")
        print(f"[Server DEBUG] WEBSOCKET_PORT configured as: {port}")
        print(f"[Server DEBUG] Waiting for connections on /ws/dlc endpoint...")
