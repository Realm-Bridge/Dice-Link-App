"""Dice Link - Physical dice rolling companion for Foundry VTT"""

import threading
import time
import uvicorn
import sys
import os
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, Qt, QObject, pyqtSlot, QPoint, QEvent, QTimer
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QDesktopServices

# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG, CONNECTION_METHOD
from upnp import setup_upnp_port_forward, remove_upnp_port_forward, get_external_ip
from debug import log_startup, log_server, log_drag_start, log_drag_move, log_drag_end, log_vtt


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


class VTTWebPage(QWebEnginePage):
    """Custom web page - only blocks external navigation"""
    
    def __init__(self, profile, allowed_origin, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin
    
    def javaScriptConsoleMessage(self, level, message, line, source):
        """Capture ALL JavaScript console output and display in our log"""
        try:
            # level is a JavaScriptConsoleMessageLevel enum, convert to int
            level_int = int(level)
            level_str = {0: "INFO", 1: "WARN", 2: "ERROR"}.get(level_int, "LOG")
            
            # Only log messages that seem relevant (errors, our debug, or PopOut related)
            if level_int >= 1 or "DLA" in message or "POPOUT" in message or "SIMULATE" in message or "error" in message.lower() or "Error" in message:
                log_vtt(f"[JS {level_str}] {message}")
                if level_int >= 2:  # For errors, also show source info
                    log_vtt(f"  Source: {source}, Line: {line}")
        except Exception as e:
            log_vtt(f"[Console Error] {message}")
        
    def is_same_origin(self, url_str: str) -> bool:
        """Check if URL is same origin as allowed Foundry server"""
        if not url_str or url_str == 'about:blank':
            return True
        
        parsed_new = urlparse(url_str)
        parsed_allowed = urlparse(self.allowed_origin)
        
        return (parsed_new.scheme == parsed_allowed.scheme and 
                parsed_new.netloc == parsed_allowed.netloc)
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Only block external navigation"""
        url_str = url.toString()
        
        if self.is_same_origin(url_str):
            return True
        
        if url_str.startswith('javascript:'):
            return True
        
        log_vtt(f"\nBLOCKED: External navigation to {url_str}")
        return False


class VTTPopupWindow(QMainWindow):
    """Window container for VTT pop-outs"""
    
    def __init__(self, web_view):
        super().__init__()
        self.web_view = web_view
        self.is_closing = False  # Flag to prevent multiple close attempts
        
        self.setWindowTitle("VTT Pop-out")
        self.resize(600, 700)
        
        self.setCentralWidget(web_view)
        
        # Update title when page title changes
        web_view.page().titleChanged.connect(self.on_title_changed)
        
        log_vtt("[POPUP] Window created")
    
    def on_title_changed(self, title):
        if title and title != "about:blank":
            self.setWindowTitle(title)

    def closeEvent(self, event):
        """Intercept OS close button - trigger the sheet's own close button instead"""
        if self.is_closing:
            # Already processing close, allow it this time
            log_vtt("[POPUP] Close already in progress, allowing close")
            event.accept()
            return
        
        log_vtt("[POPUP] OS close button clicked - triggering sheet close button")
        self.is_closing = True
        
        # Click the sheet's close button so PopOut module returns the sheet properly
        trigger_script = """
        (function() {
            var closeBtn = document.querySelector('[data-action="close"]');
            if (closeBtn) {
                console.log('[POPUP] Found close button, clicking it');
                closeBtn.click();
                return 'clicked';
            } else {
                console.log('[POPUP] Close button not found');
                return 'not_found';
            }
        })();
        """
        
        def on_result(result):
            log_vtt(f"[POPUP] Trigger close button result: {result}")
            if result == 'clicked':
                # Sheet button was clicked, wait a moment for the page to unload, then close the window
                log_vtt("[POPUP] Sheet button clicked, waiting for unload...")
                # Use a timer to wait for the unload to complete
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self.perform_close)
            else:
                # No sheet button found - close immediately
                log_vtt("[POPUP] No sheet button, closing window directly")
                self.perform_close()
        
        self.web_view.page().runJavaScript(trigger_script, on_result)
        
        # Ignore the close event for now - we'll call perform_close() when ready
        event.ignore()
    
    def perform_close(self):
        """Actually close the window"""
        log_vtt("[POPUP] Performing window close")
        self.close()  # This will call closeEvent again, but is_closing flag will allow it


class VTTViewingWindow(QMainWindow):
    """Main viewing window for VTT - closes all popups when closed"""
    
    def __init__(self, vtt_view):
        super().__init__()
        self.vtt_view = vtt_view
        
        self.setWindowTitle("VTT Viewer")
        self.setGeometry(100, 100, 1200, 800)
        self.setCentralWidget(vtt_view)
        
        log_vtt("[VIEWER] Viewing window created")
    
    def closeEvent(self, event):
        """Close all popup windows when viewing window closes"""
        log_vtt("[VIEWER] Viewing window closing - closing all popups")
        
        # Close all popup windows created by this viewing window
        if hasattr(self.vtt_view, 'popup_windows'):
            for popup_window in self.vtt_view.popup_windows:
                log_vtt(f"[VIEWER] Closing popup window")
                popup_window.close()
        
        # Allow the viewing window to close
        event.accept()


class VTTWebView(QWebEngineView):
    """
    Custom WebEngineView that properly handles window.open() by overriding createWindow().
    
    This is the KEY fix: when JavaScript calls window.open(), Qt calls createWindow()
    and the RETURNED view becomes the popup. JavaScript gets a reference to this window,
    which is what Foundry's PopOut module needs.
    """
    
    def __init__(self, allowed_origin, parent=None):
        super().__init__(parent)
        self.allowed_origin = allowed_origin
        self.popup_windows = []  # Keep references to prevent garbage collection
        
        # Set custom page for navigation blocking
        self.custom_page = VTTWebPage(self.page().profile(), allowed_origin)
        self.setPage(self.custom_page)
    
    def createWindow(self, window_type):
        """
        Override createWindow - called when JavaScript uses window.open().
        
        Create popup and inject JavaScript to expose document operations properly.
        """
        log_vtt(f"\n--- createWindow() called ---")
        log_vtt(f"Window type: {window_type}")
        
        # Create popup view that shares the SAME profile as the main page
        popup_view = QWebEngineView()
        popup_page = VTTWebPage(self.page().profile(), self.allowed_origin, popup_view)
        popup_view.setPage(popup_page)
        
        # Inject JavaScript into popup to expose document operations
        # This allows PopOut module's document.open/write/close to work
        expose_document_script = """
        (function() {
            // Ensure the popup exposes itself properly as a window
            window.__popupReady = true;
            console.log('[POPUP] Popup initialized, document available');
        })();
        """
        popup_page.runJavaScript(expose_document_script)
        
        # Create window container
        popup_window = VTTPopupWindow(popup_view)
        popup_window.show()
        
        # Keep references
        self.popup_windows.append(popup_window)
        
        log_vtt("Popup created and document exposed to JavaScript")
        
        # Return the page (not view) - this gives JavaScript a proper document interface
        # Actually, we need to return something JavaScript can interact with
        # For now return the view - Qt should handle mapping window.open() return value
        return popup_view


class VTTPopupView(QWebEngineView):
    """WebEngineView for popup windows - can create nested popups if needed"""
    
    def __init__(self, allowed_origin, parent=None):
        super().__init__(parent)
        self.allowed_origin = allowed_origin
        self.popup_windows = []
        
        # Set custom page with navigation restrictions
        self.custom_page = VTTWebPage(self.page().profile(), allowed_origin)
        self.setPage(self.custom_page)
    
    def createWindow(self, window_type):
        """Allow nested popups with same restrictions"""
        log_vtt(f"[POPUP] Nested createWindow() called")
        
        popup_view = VTTPopupView(self.allowed_origin)
        popup_window = VTTPopupWindow(popup_view)
        popup_window.show()
        self.popup_windows.append(popup_window)
        
        return popup_view


class ConnectionDialog(QDialog):
    """Dialog for entering and validating VTT server URL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to VTT Server")
        self.setMinimumWidth(400)
        self.vtt_url = None
        self.is_validating = False
        
        # Create layout
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Enter VTT Server URL:")
        layout.addWidget(label)
        
        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:30000 or https://example.com")
        layout.addWidget(self.url_input)
        
        # Error message label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ff6b6b;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        button_layout.addWidget(self.connect_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_connect(self):
        """Handle connect button click - validate the URL"""
        url = self.url_input.text().strip()
        
        if not url:
            self.show_error("Please enter a URL")
            return
        
        # Store the URL being validated
        self.validating_url = url
        
        # Update UI state
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Validating...")
        self.error_label.setVisible(False)
        
        # Validate URL (synchronous - callback called directly)
        VTTValidator.validate_url(url, self.on_validation_complete)
    
    def on_validation_complete(self, is_valid, message, data):
        """Handle validation result"""
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        
        if is_valid:
            self.vtt_url = self.validating_url
            self.accept()
        else:
            self.show_error(message)
    
    def show_error(self, message):
        """Display error message"""
        self.error_label.setText(f"Error: {message}")
        self.error_label.setVisible(True)


class WindowController(QObject):
    """Handles window control commands from JavaScript"""
    
    def __init__(self, browser, main_window=None):
        super().__init__()
        self.browser = browser
        self.main_window = main_window  # Reference to main application window
        self.mouse_offset = QPoint()  # Offset from mouse to window corner
    
    @pyqtSlot()
    def minimize(self):
        """Minimize the window"""
        self.browser.showMinimized()
    
    @pyqtSlot()
    def close(self):
        """Close the application"""
        self.browser.close()
    
    @pyqtSlot(int, int)
    def startDrag(self, x, y):
        """Start window drag - calculate offset from mouse to window corner"""
        # JavaScript sends screenX/screenY (global screen coordinates)
        global_mouse_pos = QPoint(x, y)
        window_pos = self.browser.pos()
        # Store offset: how far from window corner the mouse clicked
        self.mouse_offset = window_pos - global_mouse_pos
    
    @pyqtSlot(int, int)
    def doDrag(self, x, y):
        """Perform window drag - move window so mouse stays at same relative position"""
        if self.mouse_offset.isNull():
            return
        # JavaScript sends screenX/screenY (global screen coordinates)
        global_mouse_pos = QPoint(x, y)
        # Window position = mouse position + stored offset
        new_window_pos = global_mouse_pos + self.mouse_offset
        self.browser.move(new_window_pos)
    
    @pyqtSlot()
    def openConnectionDialog(self):
        """Open connection dialog to enter VTT server URL"""
        dialog = ConnectionDialog(self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.vtt_url:
            # Launch VTT viewing window
            self.launch_vtt_window(dialog.vtt_url)
    
    def launch_vtt_window(self, url):
        """Launch a new window to view the VTT"""
        # Store reference to prevent garbage collection
        if not hasattr(self, 'vtt_windows'):
            self.vtt_windows = []
        
        allowed_origin = url.rstrip('/')
        
        # Create VTT web view with allowed origin
        vtt_view = VTTWebView(allowed_origin)
        
        # Create viewing window (which will close all popups when closed)
        vtt_window = VTTViewingWindow(vtt_view)
        
        # Load the URL
        vtt_view.load(QUrl(url))
        
        vtt_window.show()
        
        # Keep reference
        self.vtt_windows.append(vtt_window)
    
    @pyqtSlot(str)
    def openUrl(self, url):
        """Open URL in system default browser"""
        QDesktopServices.openUrl(QUrl(url))


class DraggableWebEngineView(QWebEngineView):
    """Custom QWebEngineView with frameless window dragging support"""
    
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.is_dragging = False
        self.window_controller = None  # Will be set after creation
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        # Check if click is in title bar area (top 80px)
        if event.position().y() < 80:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            log_drag_start(event.globalPosition(), self.drag_position, self.pos())
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if self.is_dragging:
            global_pos_float = event.globalPosition()
            global_pos_int = global_pos_float.toPoint()
            calculated_pos = global_pos_int - self.drag_position
            current_window_pos = self.pos()
            log_drag_move(global_pos_float, global_pos_int, self.drag_position, calculated_pos, current_window_pos)
            self.move(calculated_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.is_dragging = False
        log_drag_end()
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        # F12 prints DevTools URL to console
        if event.key() == Qt.Key.Key_F12:
            print("[DevTools] Open http://localhost:9222 in a browser to debug")
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle main window close - close all child VTT windows"""
        if self.window_controller and hasattr(self.window_controller, 'vtt_windows'):
            # Close all VTT windows
            for vtt_window in self.window_controller.vtt_windows:
                vtt_window.close()
        
        # Allow the main window to close
        event.accept()


def run_server():
    """Run the FastAPI server in a background thread"""
    uvicorn.run(
        "server:app",
        host=WEBSOCKET_HOST,
        port=WEBSOCKET_PORT,
        reload=False,
        log_level="info" if DEBUG else "warning"
    )


def main():
    """Main entry point for Dice Link - launches desktop app with PyQt5"""
    # Print startup banner
    print(f"\n{'='*50}")
    print(f"  {APP_NAME}")
    print(f"  Physical dice rolling for Foundry VTT")
    print(f"{'='*50}\n")
    
    log_server("Starting Dice Link Desktop App...")
    log_startup(WEBSOCKET_HOST, WEBSOCKET_PORT)
    log_server(f"Server running on http://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    log_server(f"UI available at http://localhost:{WEBSOCKET_PORT}")
    
    # Show connection method info
    if CONNECTION_METHOD == "webrtc":
        log_server(f"Connection method: WebRTC (bypasses browser security restrictions)")
        log_server(f"DLC connects via WebRTC handshake at http://localhost:{WEBSOCKET_PORT}/api/receive-offer")
    else:
        log_server(f"Connection method: WebSocket (fallback mode)")
        log_server(f"DLC module connects to ws://[hostname]:{WEBSOCKET_PORT}/ws/dlc")
    
    # UPnP is only relevant for WebSocket fallback mode (remote connections)
    # For WebRTC on localhost, no port forwarding is needed
    upnp_success = False
    external_ip = None
    if CONNECTION_METHOD == "websocket":
        # Attempt UPnP port forwarding for remote connections
        upnp_success, external_ip = setup_upnp_port_forward(WEBSOCKET_PORT)
        if upnp_success:
            log_server("Remote connections enabled!")
            log_server(f"Players should configure DLC to connect to: {external_ip}")
        else:
            if external_ip:
                log_server("Automatic port forwarding unavailable")
                log_server(f"Your external IP is: {external_ip}")
                log_server(f"For remote connections, manually forward port {WEBSOCKET_PORT} in your router")
            else:
                log_server("Could not determine external IP or set up port forwarding")
                log_server("Remote connections may require manual router configuration")
    else:
        log_server("UPnP skipped (not needed for localhost WebRTC connections)")
    
    # Start the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1.5)
    
    # Create and display the PyQt6 window
    app = QApplication(sys.argv)
    
    # Enable DevTools via environment variable - must be set before creating the profile
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
    
    # Create profile with devtools enabled
    profile = QWebEngineProfile.defaultProfile()
    
    # Create a draggable web view widget
    browser = DraggableWebEngineView()
    browser.setPage(browser.page())  # Ensure page is initialized
    
    # Enable transparent background for rounded corners
    browser.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    
    # Set up window controller for frameless window control
    window_controller = WindowController(browser, browser)
    browser.window_controller = window_controller  # Store reference for closeEvent
    
    # Set window properties
    browser.setWindowTitle(APP_NAME)
    browser.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    
    # Set up web channel for JavaScript-to-Python communication
    channel = QWebChannel()
    channel.registerObject("pyqtBridge", window_controller)
    browser.page().setWebChannel(channel)
    
    # Lock window to fixed size - cannot be resized
    # Original planned size - will be scaled by device pixel ratio
    fixed_width = 1788
    fixed_height = 1500
    
    # Store fixed size and browser reference for dynamic scaling
    browser.fixed_width = fixed_width
    browser.fixed_height = fixed_height
    
    # Function to update scaling when DPI changes
    def update_dpi_scaling():
        screen = browser.screen()
        device_pixel_ratio = screen.devicePixelRatio() if screen else 1.0
        
        # Calculate scaled window size
        scaled_width = int(browser.fixed_width / device_pixel_ratio)
        scaled_height = int(browser.fixed_height / device_pixel_ratio)
        
        # Update window size
        browser.setFixedSize(scaled_width, scaled_height)
        
        # Update zoom factor - inverse of device ratio so content scales DOWN with window
        # If device ratio is 2.0 (200% scaling), zoom should be 0.5 to fit content in half-sized window
        browser.setZoomFactor(1.0 / device_pixel_ratio)
        
        print(f"[DPI UPDATE] Device pixel ratio: {device_pixel_ratio}, Window size: {scaled_width}x{scaled_height}")
    
    # Initial scaling
    update_dpi_scaling()
    
    # Connect to screen DPI changes
    screen = browser.screen()
    if screen:
        screen.logicalDotsPerInchChanged.connect(update_dpi_scaling)
        # If window moves to different display, also update scaling
        screen.geometryChanged.connect(update_dpi_scaling)
    
    # Load the local server URL (always use localhost for browser, even if server binds to 0.0.0.0)
    browser_host = "localhost" if WEBSOCKET_HOST == "0.0.0.0" else WEBSOCKET_HOST
    url = f"http://{browser_host}:{WEBSOCKET_PORT}"
    browser.load(QUrl(url))
    
    # Show the window and start the application
    browser.show()
    
    # Run the application
    exit_code = app.exec()
    
    # Clean up UPnP port forwarding on exit
    if upnp_success:
        log_server("Cleaning up port forwarding...")
        remove_upnp_port_forward(WEBSOCKET_PORT)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


