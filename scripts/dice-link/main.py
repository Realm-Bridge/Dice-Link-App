"""Dice Link - Physical dice rolling companion for Foundry VTT"""

import threading
import time
import uvicorn
import sys
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, Qt, QObject, pyqtSlot, QPoint, QEvent
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QDesktopServices

# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG, CONNECTION_METHOD
from upnp import setup_upnp_port_forward, remove_upnp_port_forward, get_external_ip
from debug import log_startup, log_server, log_drag_start, log_drag_move, log_drag_end


class VTTValidator:
    """Validates VTT URLs by checking for API endpoints or Foundry markers"""
    
    @staticmethod
    def validate(url, callback):
        """Validate VTT URL in a separate thread
        
        Args:
            url: VTT server URL to validate
            callback: Function to call with (is_valid, message, data) when done
        """
        def validate_thread():
            try:
                # Ensure URL has a scheme
                if not url.startswith(('http://', 'https://')):
                    url_to_check = f'http://{url}'
                else:
                    url_to_check = url
                
                # Try to get the root page to check for VTT markers
                try:
                    req = urllib.request.Request(f'{url_to_check}/api/status', headers={'User-Agent': 'Dice Link'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        # If /api/status exists, it's likely a Foundry instance
                        callback(True, 'Valid Foundry instance detected', {'url': url_to_check})
                        return
                except (urllib.error.HTTPError, urllib.error.URLError):
                    # /api/status failed, try checking the root page for Foundry markers
                    pass
                
                # Check root page for Foundry HTML markers
                try:
                    req = urllib.request.Request(url_to_check, headers={'User-Agent': 'Dice Link'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        if any(marker in html.lower() for marker in ['foundry', 'vtt', '/ui/players', 'socket']):
                            callback(True, 'VTT instance detected', {'url': url_to_check})
                        else:
                            callback(False, 'URL does not appear to be a valid VTT', {})
                except (urllib.error.HTTPError, urllib.error.URLError) as e:
                    callback(False, f'Could not connect to URL: {str(e)}', {})
            except Exception as e:
                callback(False, f'Validation error: {str(e)}', {})
        
        # Run validation in background thread to avoid blocking UI
        thread = threading.Thread(target=validate_thread, daemon=True)
        thread.start()


class VTTWebPage(QWebEnginePage):
    """Custom web page for VTT viewing - blocks external navigation"""
    
    def acceptNavigationRequest(self, url, navigation_type, is_redirect):
        """Only allow navigation within the same origin"""
        if not hasattr(self, 'base_url'):
            return True
        
        # Allow same-origin navigation
        if url.host() == self.base_url.host() and url.scheme() == self.base_url.scheme():
            return True
        
        # Block external navigation
        return False


class VTTWebView(QWebEngineView):
    """Custom web view for displaying VTT instances"""
    
    def __init__(self, url):
        super().__init__()
        self.base_url = QUrl(url)
        
        # Create custom page and set base URL for origin checking
        page = VTTWebPage(self)
        page.base_url = self.base_url
        self.setPage(page)
        
        # Load the VTT
        self.load(self.base_url)
    
    def createWindow(self, window_type):
        """Handle window.open() calls from the VTT - open in new windows"""
        new_view = VTTWebView(self.base_url.toString())
        new_view.show()
        return new_view


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
        
        # Start validation
        self.is_validating = True
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Validating...")
        self.error_label.setVisible(False)
        
        # Validate URL
        VTTValidator.validate(url, self.on_validation_complete)
    
    def on_validation_complete(self, is_valid, message, data):
        """Handle validation result"""
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        self.is_validating = False
        
        if is_valid:
            self.vtt_url = data.get('url')
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
        vtt_window = QMainWindow()
        vtt_window.setWindowTitle("VTT Viewer")
        vtt_window.setGeometry(100, 100, 1200, 800)
        
        # Create VTT web view
        vtt_view = VTTWebView(url)
        vtt_window.setCentralWidget(vtt_view)
        vtt_window.show()
    
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


