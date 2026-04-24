"""VTT Validator - Validates if a URL points to a Foundry VTT server"""

import json
import urllib.request
import urllib.error


class VTTValidator:
    """Validates if a URL points to a Foundry VTT server"""
    
    @staticmethod
    def validate_url(url: str, callback):
        """
        Check if URL is a valid Foundry VTT server.
        
        Foundry indicators:
        - Page title contains "Foundry Virtual Tabletop"
        - Has /api/status endpoint
        - Returns specific HTML structure
        """
        try:
            # Try the /api/status endpoint (Foundry v9+)
            api_url = url.rstrip('/') + '/api/status'
            req = urllib.request.Request(api_url, headers={'User-Agent': 'DLA-Validator/1.0'})
            
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = response.read().decode('utf-8')
                    # Foundry returns JSON with specific fields
                    try:
                        status = json.loads(data)
                        if 'active' in status or 'users' in status:
                            callback(True, "Foundry API status endpoint found", status)
                            return
                    except json.JSONDecodeError:
                        pass
            except urllib.error.HTTPError as e:
                # 404 is expected if not Foundry, but other errors might indicate it's there
                if e.code == 403:
                    # Forbidden could mean it's Foundry but requires auth
                    callback(True, "Foundry detected (API requires authentication)", None)
                    return
            
            # Fallback: Try loading the main page and checking for Foundry markers
            req = urllib.request.Request(url, headers={'User-Agent': 'DLA-Validator/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Check for Foundry-specific markers
                foundry_markers = [
                    'Foundry Virtual Tabletop',
                    'foundryvtt',
                    'game.ready',
                    'FoundryVTT'
                ]
                
                for marker in foundry_markers:
                    if marker.lower() in html.lower():
                        callback(True, f"Foundry marker found: '{marker}'", None)
                        return
                
                # Not Foundry
                callback(False, "No Foundry markers found in page", None)
                
        except urllib.error.URLError as e:
            callback(False, f"Connection failed: {e.reason}", None)
        except Exception as e:
            callback(False, f"Validation error: {str(e)}", None)
