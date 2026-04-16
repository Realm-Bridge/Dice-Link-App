"""UPnP port forwarding module using miniupnpc"""

import socket
import miniupnpc

# Store the UPnP client for cleanup on exit
_upnp_client = None


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine our local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def setup_upnp_port_forward(port: int, description: str = "Dice Link") -> bool:
    """
    Attempt to set up UPnP port forwarding for the given port.
    
    Args:
        port: The port number to forward
        description: Description for the port mapping
        
    Returns:
        True if port forwarding was successfully set up, False otherwise
    """
    global _upnp_client
    
    try:
        print(f"[UPnP] Discovering UPnP devices...")
        
        # Create UPnP client
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200  # 200ms discovery delay
        
        # Discover UPnP devices
        devices_found = upnp.discover()
        
        if devices_found == 0:
            print(f"[UPnP] No UPnP devices found - remote connections will require manual port forwarding")
            return False
        
        print(f"[UPnP] Found {devices_found} UPnP device(s)")
        
        # Select the IGD (Internet Gateway Device)
        upnp.selectigd()
        
        # Get external IP
        external_ip = upnp.externalipaddress()
        print(f"[UPnP] External IP: {external_ip}")
        
        # Get local IP for port mapping
        local_ip = get_local_ip()
        print(f"[UPnP] Local IP: {local_ip}")
        
        # Add port mapping (TCP for WebSocket)
        # Parameters: external_port, protocol, internal_ip, internal_port, description, remote_host, lease_duration
        result = upnp.addportmapping(
            port,           # external port
            'TCP',          # protocol
            local_ip,       # internal IP (this machine)
            port,           # internal port
            description,    # description
            ''              # remote host (empty = any)
        )
        
        if result:
            print(f"[UPnP] Successfully forwarded port {port} ({local_ip}:{port} -> {external_ip}:{port})")
            _upnp_client = upnp
            return True
        else:
            print(f"[UPnP] Failed to add port mapping - remote connections will require manual port forwarding")
            return False
            
    except Exception as e:
        print(f"[UPnP] Error during UPnP setup: {e}")
        print(f"[UPnP] Remote connections will require manual port forwarding")
        return False


def remove_upnp_port_forward(port: int) -> bool:
    """
    Remove the UPnP port forwarding rule on exit.
    
    Args:
        port: The port number to unforward
        
    Returns:
        True if successfully removed, False otherwise
    """
    global _upnp_client
    
    if not _upnp_client:
        return False
    
    try:
        result = _upnp_client.deleteportmapping(port, 'TCP')
        if result:
            print(f"[UPnP] Removed port forwarding for port {port}")
            return True
        else:
            print(f"[UPnP] Could not remove port forwarding for port {port}")
            return False
    except Exception as e:
        print(f"[UPnP] Error removing port forwarding: {e}")
        return False
