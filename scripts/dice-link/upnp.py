"""UPnP port forwarding module using upnpy (pure Python)"""

import socket
import urllib.request
from debug import log_upnp, log_upnp_device, log_upnp_services, log_upnp_service_detail, log_upnp_error

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
        log_upnp("upnpy library not installed - run: pip install upnpy")
        return False, None

    try:
        log_upnp("Discovering UPnP devices...")

        # Create UPnP client and discover devices
        upnp = upnpy.UPnP()

        try:
            devices = upnp.discover(delay=2)
        except Exception as e:
            log_upnp(f"Discovery failed: {e}")
            log_upnp("Trying external IP lookup as fallback...")
            ext_ip = get_external_ip_fallback()
            if ext_ip:
                _external_ip = ext_ip
                log_upnp(f"External IP (via web): {ext_ip}")
                log_upnp("UPnP port forwarding unavailable - manual port forwarding required")
                return False, ext_ip
            return False, None

        if not devices:
            log_upnp("No UPnP devices found")
            ext_ip = get_external_ip_fallback()
            if ext_ip:
                _external_ip = ext_ip
                log_upnp(f"External IP (via web): {ext_ip}")
            return False, ext_ip

        log_upnp(f"Found {len(devices)} UPnP device(s)")

        # Find an IGD (Internet Gateway Device) with WANIPConnection service
        igd_device = None
        wan_service = None

        for device in devices:
            log_upnp_device(device.friendly_name, getattr(device, 'type_', 'unknown'))

            try:
                # List all available services for debugging
                services = device.get_services()
                log_upnp_services(services)

                # Look for WANIPConnection or WANPPPConnection service
                # Note: get_services() returns service objects directly, not IDs
                for service in services:
                    try:
                        # Get service type string for matching
                        service_type = str(service).lower()
                        service_id_str = str(service)

                        # Check for available actions on this service
                        actions = None
                        if hasattr(service, 'get_actions'):
                            try:
                                actions = service.get_actions()
                            except Exception as action_err:
                                log_upnp_service_detail(service_id_str, error=str(action_err))

                        log_upnp_service_detail(service_id_str, service_type=service_type, actions=actions)

                        if 'wanipconnection' in service_type or 'wanpppconnection' in service_type:
                            igd_device = device
                            wan_service = service
                            log_upnp(f"Found gateway service: {service_id_str}")
                            break
                    except Exception as service_err:
                        log_upnp_service_detail(str(service), error=str(service_err))
                        continue

            except Exception as e:
                import traceback
                log_upnp_error("checking device services", str(e), traceback.format_exc())
                continue

            if wan_service:
                break

        if not wan_service:
            log_upnp("No compatible gateway device found")
            ext_ip = get_external_ip_fallback()
            if ext_ip:
                _external_ip = ext_ip
                log_upnp(f"External IP (via web): {ext_ip}")
            return False, ext_ip

        # Get external IP from router
        try:
            ext_ip_response = wan_service.GetExternalIPAddress()
            _external_ip = ext_ip_response.get('NewExternalIPAddress', None)
            log_upnp(f"External IP (from router): {_external_ip}")
        except Exception as e:
            log_upnp(f"Could not get external IP from router: {e}")
            _external_ip = get_external_ip_fallback()
            if _external_ip:
                log_upnp(f"External IP (via web): {_external_ip}")

        # Get local IP
        local_ip = get_local_ip()
        log_upnp(f"Local IP: {local_ip}")

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
                NewLeaseDuration=3600  # 1 hour lease - some routers handle this better than 0
            )

            log_upnp(f"Successfully forwarded port {port}")
            log_upnp(f"Mapping: {_external_ip}:{port} -> {local_ip}:{port}")

            # Store for cleanup
            _upnp_device = igd_device
            _upnp_service = wan_service
            _forwarded_port = port

            return True, _external_ip

        except Exception as e:
            error_str = str(e)
            if '718' in error_str:
                log_upnp(f"Port {port} mapping already exists (possibly from previous session)")
                return True, _external_ip
            elif '725' in error_str:
                log_upnp("Router rejected mapping - may need to enable UPnP in router settings")
            else:
                log_upnp(f"Failed to add port mapping: {e}")
            return False, _external_ip

    except Exception as e:
        log_upnp(f"Error during UPnP setup: {e}")
        ext_ip = get_external_ip_fallback()
        if ext_ip:
            _external_ip = ext_ip
            log_upnp(f"External IP (via web): {ext_ip}")
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
        log_upnp(f"Removed port forwarding for port {port_to_remove}")
        return True
    except Exception as e:
        log_upnp(f"Error removing port forwarding: {e}")
        return False
