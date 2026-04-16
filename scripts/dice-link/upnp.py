"""UPnP port forwarding module using upnpy"""

import asyncio
from typing import Optional
from upnpy import UPnP

# Store the UPnP device for cleanup on exit
_upnp_device = None


def setup_upnp_port_forward(port: int, description: str = "Dice Link") -> bool:
    """
    Attempt to set up UPnP port forwarding for the given port.
    
    Args:
        port: The port number to forward
        description: Description for the port mapping
        
    Returns:
        True if port forwarding was successfully set up, False otherwise
    """
    global _upnp_device
    
    try:
        print(f"[UPnP] Discovering UPnP devices...")
        upnp = UPnP()
        devices = upnp.discover()
        
        if not devices:
            print(f"[UPnP] No UPnP devices found - remote connections will require manual port forwarding")
            return False
        
        print(f"[UPnP] Found {len(devices)} UPnP device(s)")
        
        # Try to find an IGD (Internet Gateway Device) which handles port mapping
        igd = None
        for device in devices:
            try:
                # Check if this device supports port mapping
                if hasattr(device, 'AddPortMapping'):
                    igd = device
                    break
            except:
                continue
        
        if not igd:
            print(f"[UPnP] No IGD device found - remote connections will require manual port forwarding")
            return False
        
        # Get the external IP to display to user
        try:
            external_ip = igd.GetExternalIPAddress()
            print(f"[UPnP] External IP: {external_ip}")
        except:
            external_ip = "unknown"
        
        # Add port mapping (TCP for WebSocket)
        try:
            igd.AddPortMapping(
                NewRemoteHost='',
                NewExternalPort=port,
                NewProtocol='TCP',
                NewInternalPort=port,
                NewInternalClient='127.0.0.1',
                NewEnabled='1',
                NewPortMappingDescription=description,
                NewLeaseDuration=0  # 0 means infinite
            )
            
            print(f"[UPnP] Successfully forwarded port {port} via UPnP")
            _upnp_device = igd
            return True
            
        except Exception as e:
            print(f"[UPnP] Failed to add port mapping: {e}")
            return False
            
    except Exception as e:
        print(f"[UPnP] Error during UPnP setup: {e}")
        return False


def remove_upnp_port_forward(port: int) -> bool:
    """
    Remove the UPnP port forwarding rule on exit.
    
    Args:
        port: The port number to unforward
        
    Returns:
        True if successfully removed, False otherwise
    """
    global _upnp_device
    
    if not _upnp_device:
        return False
    
    try:
        _upnp_device.DeletePortMapping(
            NewRemoteHost='',
            NewExternalPort=port,
            NewProtocol='TCP'
        )
        print(f"[UPnP] Removed port forwarding for port {port}")
        return True
    except Exception as e:
        print(f"[UPnP] Error removing port forwarding: {e}")
        return False
