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
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QWidget, QSizePolicy
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QFontDatabase, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, Qt, QObject, pyqtSlot, pyqtSignal, QPoint, QEvent, QTimer
from PyQt6.QtWebChannel import QWebChannel
# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG, CONNECTION_METHOD
from upnp import setup_upnp_port_forward, remove_upnp_port_forward, get_external_ip
from debug import log_startup, log_server, log_drag_start, log_drag_move, log_drag_end, log_vtt, log_connection_monitor
from bridge_state import set_bridge
from custom_window import CustomWindow, CustomTitleBar, ResizeGrip
from vtt_validator import VTTValidator
from dialogs import ConnectionDialog
from dla_bridge import DLABridge
from vtt_web import VTTWebPage, VTTWebView, VTTPopupView, DraggableWebEngineView
from vtt_windows import VTTPopupWindow, VTTViewingWindow
from window_controller import WindowController










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
    
    # Set window icon for taskbar branding
    logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background.png"
    if logo_path.exists():
        pixmap = QPixmap(str(logo_path))
        # Scale to 2.5x larger for better taskbar visibility
        scaled_pixmap = pixmap.scaledToWidth(int(pixmap.width() * 2.5), Qt.TransformationMode.SmoothTransformation)
        browser.setWindowIcon(QIcon(scaled_pixmap))
    
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


