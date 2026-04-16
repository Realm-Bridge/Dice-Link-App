"""UPnP port forwarding for Dice Link"""

import logging

# Try to import upnp_forwarder, but don't fail if not available
try:
    from upnp_forwarder import add_port_mapping, delete_port_mapping, UPnPError
    UPNP_AVAILABLE = True
except ImportError:
    UPNP_AVAILABLE = False
    UPnPError = Exception  # Fallback for type hints

logger = logging.getLogger(__name__)


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
        logger.warning("UPnP library not available. Install with: pip install upnp-forwarder")
        print("[UPnP] Library not available - remote connections may require manual port forwarding")
        return False
    
    try:
        # Attempt to add port mapping
        # local_port and external_port are the same
        # protocol is TCP for WebSocket connections
        # lease_duration of 0 means infinite (until router restart or explicit delete)
        success = add_port_mapping(
            local_port=port,
            external_port=port,
            protocol='TCP',
            description=description,
            lease_duration=0  # Infinite lease
        )
        
        if success:
            print(f"[UPnP] Successfully forwarded port {port}")
            logger.info(f"UPnP port forwarding enabled for port {port}")
            return True
        else:
            print(f"[UPnP] Failed to forward port {port} - remote connections may require manual port forwarding")
            logger.warning(f"UPnP port forwarding failed for port {port}")
            return False
            
    except UPnPError as e:
        print(f"[UPnP] Error: {e} - remote connections may require manual port forwarding")
        logger.warning(f"UPnP error: {e}")
        return False
    except Exception as e:
        print(f"[UPnP] Unexpected error: {e}")
        logger.error(f"Unexpected UPnP error: {e}")
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
        success = delete_port_mapping(
            external_port=port,
            protocol='TCP'
        )
        
        if success:
            print(f"[UPnP] Removed port forwarding for port {port}")
            logger.info(f"UPnP port forwarding removed for port {port}")
            return True
        else:
            logger.warning(f"Failed to remove UPnP port forwarding for port {port}")
            return False
            
    except UPnPError as e:
        logger.warning(f"UPnP error while removing port forward: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while removing UPnP port forward: {e}")
        return False


def is_upnp_available() -> bool:
    """Check if UPnP library is available"""
    return UPNP_AVAILABLE
