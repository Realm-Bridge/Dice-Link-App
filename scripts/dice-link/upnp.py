"""UPnP port forwarding for Dice Link"""

import logging
import socket

# Try to import upnp_port_forward (pure Python, no compilation needed)
try:
    from upnp_port_forward import forward_port, remove_port_forward
    UPNP_AVAILABLE = True
except ImportError:
    UPNP_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def setup_upnp_port_forward(port: int, description: str = "Dice Link") -> bool:
    """
    Attempt to set up UPnP port forwarding for the specified port.
    
    Args:
        port: The port to forward
        description: Description for the port mapping
        
    Returns:
        True if port forwarding was successful, False otherwise
    """
    if not UPNP_AVAILABLE:
        logger.warning("UPnP library not available. Install with: pip install upnp-port-forward")
        print("[UPnP] Library not available - remote connections may require manual port forwarding")
        return False
    
    try:
        local_ip = get_local_ip()
        print(f"[UPnP] Attempting to forward port {port} to {local_ip}...")
        
        # forward_port returns external IP if successful
        external_ip = forward_port(port)
        
        if external_ip:
            print(f"[UPnP] Successfully forwarded port {port}")
            print(f"[UPnP] External IP: {external_ip}")
            logger.info(f"UPnP port forwarding enabled for port {port}, external IP: {external_ip}")
            return True
        else:
            print(f"[UPnP] Failed to forward port {port} - remote connections may require manual port forwarding")
            logger.warning(f"UPnP port forwarding failed for port {port}")
            return False
            
    except Exception as e:
        print(f"[UPnP] Error: {e} - remote connections may require manual port forwarding")
        logger.error(f"UPnP error: {e}")
        return False


def remove_upnp_port_forward(port: int) -> bool:
    """
    Remove UPnP port forwarding for the specified port.
    
    Args:
        port: The port to remove forwarding for
        
    Returns:
        True if removal was successful, False otherwise
    """
    if not UPNP_AVAILABLE:
        return False
    
    try:
        remove_port_forward(port)
        print(f"[UPnP] Removed port forwarding for port {port}")
        logger.info(f"UPnP port forwarding removed for port {port}")
        return True
            
    except Exception as e:
        logger.warning(f"Error while removing UPnP port forward: {e}")
        return False


def is_upnp_available() -> bool:
    """Check if UPnP library is available"""
    return UPNP_AVAILABLE
