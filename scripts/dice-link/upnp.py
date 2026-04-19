"""UPnP port forwarding module using upnpy (pure Python)"""

import socket
import urllib.request

# Store UPnP state for cleanup on exit
_upnp_device = None
_upnp_service = None
_forwarded_port = None
_external_ip = None


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def get_external_ip_fallback() -> str:
    """Get external IP via web service as fallback."""
    try:
        with urllib.request.urlopen('https://api.ipify.org', timeout=5) as response:
            return response.read().decode('utf-8').strip()
    except Exception:
        return None


def get_external_ip() -> str:
    """Get the external IP address. Returns cached value if available."""
    global _external_ip
    if _external_ip:
        return _external_ip
    return get_external_ip_fallback()


def setup_upnp_port_forward(port: int, description: str = "Dice Link") -> tuple[bool, str]:
    """
    Attempt to set up UPnP port forwarding for the given port.
    
    Args:
        port: The port number to forward
        description: Description for the port mapping
        
    Returns:
        Tuple of (success: bool, external_ip: str or None)
    """
    global _upnp_device, _upnp_service, _forwarded_port, _external_ip
    
    try:
        import upnpy
    except ImportError:
        print("[UPnP] upnpy library not installed - run: pip install upnpy")
        return False, None
    
    try:
        print("[UPnP] Discovering UPnP devices...")
        
        # Create UPnP client and discover devices
        upnp = upnpy.UPnP()
        
        try:
            devices = upnp.discover(delay=2)
        except Exception as e:
            print(f"[UPnP] Discovery failed: {e}")
            print("[UPnP] Trying external IP lookup as fallback...")
            ext_ip = get_external_ip_fallback()
            if ext_ip:
                _external_ip = ext_ip
                print(f"[UPnP] External IP (via web): {ext_ip}")
                print("[UPnP] UPnP port forwarding unavailable - manual port forwarding required")
                return False, ext_ip
            return False, None
        
        if not devices:
            print("[UPnP] No UPnP devices found")
            ext_ip = get_external_ip_fallback()
            if ext_ip:
                _external_ip = ext_ip
                print(f"[UPnP] External IP (via web): {ext_ip}")
            return False, ext_ip
        
        print(f"[UPnP] Found {len(devices)} UPnP device(s)")
        
        # Find an IGD (Internet Gateway Device) with WANIPConnection service
        igd_device = None
        wan_service = None
        
        for device in devices:
            print(f"[UPnP DEBUG] Checking device: {device.friendly_name}")
            print(f"[UPnP DEBUG] Device type: {getattr(device, 'type_', 'unknown')}")
            
            try:
                # List all available services for debugging
                services = device.get_services()
                print(f"[UPnP DEBUG] Available services: {services}")
                
                # Look for WANIPConnection or WANPPPConnection service
                for service_id in services:
                    print(f"[UPnP DEBUG] Examining service: {service_id}")
                    try:
                        service = device[service_id]
                        service_type = str(service.service).lower() if hasattr(service, 'service') else str(service).lower()
                        print(f"[UPnP DEBUG] Service type string: {service_type}")
                        
                        # Check for available actions on this service
                        if hasattr(service, 'get_actions'):
                            try:
                                actions = service.get_actions()
                                print(f"[UPnP DEBUG] Service actions: {actions}")
                            except Exception as action_err:
                                print(f"[UPnP DEBUG] Could not get actions: {action_err}")
                        
                        if 'wanipconnection' in service_type or 'wanpppconnection' in service_type:
                            igd_device = device
                            wan_service = service
                            print(f"[UPnP] Found gateway service: {service_id}")
                            break
                    except Exception as service_err:
                        print(f"[UPnP DEBUG] Error accessing service {service_id}: {service_err}")
                        continue
                        
            except Exception as e:
                print(f"[UPnP DEBUG] Error checking device services: {e}")
                import traceback
                print(f"[UPnP DEBUG] Traceback: {traceback.format_exc()}")
                continue
            
            if wan_service:
                break
        
        if not wan_service:
            print("[UPnP] No compatible gateway device found")
            ext_ip = get_external_ip_fallback()
            if ext_ip:
                _external_ip = ext_ip
                print(f"[UPnP] External IP (via web): {ext_ip}")
            return False, ext_ip
        
        # Get external IP from router
        try:
            ext_ip_response = wan_service.GetExternalIPAddress()
            _external_ip = ext_ip_response.get('NewExternalIPAddress', None)
            print(f"[UPnP] External IP (from router): {_external_ip}")
        except Exception as e:
            print(f"[UPnP] Could not get external IP from router: {e}")
            _external_ip = get_external_ip_fallback()
            if _external_ip:
                print(f"[UPnP] External IP (via web): {_external_ip}")
        
        # Get local IP
        local_ip = get_local_ip()
        print(f"[UPnP] Local IP: {local_ip}")
        
        # Add port mapping
        try:
            wan_service.AddPortMapping(
                NewRemoteHost='',
                NewExternalPort=port,
                NewProtocol='TCP',
                NewInternalPort=port,
                NewInternalClient=local_ip,
                NewEnabled=1,
                NewPortMappingDescription=description,
                NewLeaseDuration=0  # 0 = permanent until removed
            )
            
            print(f"[UPnP] Successfully forwarded port {port}")
            print(f"[UPnP] Mapping: {_external_ip}:{port} -> {local_ip}:{port}")
            
            # Store for cleanup
            _upnp_device = igd_device
            _upnp_service = wan_service
            _forwarded_port = port
            
            return True, _external_ip
            
        except Exception as e:
            error_str = str(e)
            if '718' in error_str:
                print(f"[UPnP] Port {port} mapping already exists (possibly from previous session)")
                return True, _external_ip
            elif '725' in error_str:
                print(f"[UPnP] Router rejected mapping - may need to enable UPnP in router settings")
            else:
                print(f"[UPnP] Failed to add port mapping: {e}")
            return False, _external_ip
            
    except Exception as e:
        print(f"[UPnP] Error during UPnP setup: {e}")
        ext_ip = get_external_ip_fallback()
        if ext_ip:
            _external_ip = ext_ip
            print(f"[UPnP] External IP (via web): {ext_ip}")
        return False, ext_ip


def remove_upnp_port_forward(port: int = None) -> bool:
    """
    Remove the UPnP port forwarding rule on exit.
    
    Args:
        port: The port number to unforward (uses stored port if None)
        
    Returns:
        True if successfully removed, False otherwise
    """
    global _upnp_service, _forwarded_port
    
    if not _upnp_service:
        return False
    
    port_to_remove = port or _forwarded_port
    if not port_to_remove:
        return False
    
    try:
        _upnp_service.DeletePortMapping(
            NewRemoteHost='',
            NewExternalPort=port_to_remove,
            NewProtocol='TCP'
        )
        print(f"[UPnP] Removed port forwarding for port {port_to_remove}")
        return True
    except Exception as e:
        print(f"[UPnP] Error removing port forwarding: {e}")
        return False
