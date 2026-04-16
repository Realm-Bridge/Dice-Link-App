"""Dice Link - Physical dice rolling companion for Foundry VTT"""

import threading
import time
import uvicorn
import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot, QPoint, QEvent
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QPainterPath, QRegion, QDesktopServices

# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG
from upnp import setup_upnp_port_forward, remove_upnp_port_forward


class WindowController(QObject):
    """Handles window control commands from JavaScript"""
    
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.drag_start_pos = QPoint()
    
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
        """Start window drag - store initial mouse position relative to window"""
        self.drag_start_pos = QPoint(x, y)
    
    @pyqtSlot(int, int)
    def doDrag(self, x, y):
        """Perform window drag - move window based on new mouse position"""
        if self.drag_start_pos.isNull():
            return
        delta = QPoint(x, y) - self.drag_start_pos
        new_pos = self.browser.pos() + delta
        self.browser.move(new_pos)
    
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
        if event.y() < 80:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if self.is_dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.is_dragging = False
        super().mouseReleaseEvent(event)


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
    print(f"\n{'='*50}")
    print(f"  {APP_NAME}")
    print(f"  Physical dice rolling for Foundry VTT")
    print(f"{'='*50}\n")
    print(f"Starting Dice Link Desktop App...")
    print(f"Server running on http://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    print(f"UI available at http://localhost:{WEBSOCKET_PORT}")
    print(f"DLC module connects to ws://[hostname]:{WEBSOCKET_PORT}/ws/dlc")
    
    # Attempt to set up UPnP port forwarding for remote connections
    upnp_success = setup_upnp_port_forward(WEBSOCKET_PORT)
    
    # Start the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1.5)
    
    # Create and display the PyQt5 window
    app = QApplication(sys.argv)
    
    # Create a draggable web view widget
    browser = DraggableWebEngineView()
    
    # Enable transparent background for rounded corners
    browser.setAttribute(Qt.WA_TranslucentBackground, True)
    
    # Set up window controller for frameless window control
    window_controller = WindowController(browser)
    
    # Set window properties
    browser.setWindowTitle(APP_NAME)
    browser.setWindowFlags(Qt.FramelessWindowHint)
    
    # Set up web channel for JavaScript-to-Python communication
    channel = QWebChannel()
    channel.registerObject("pyqtBridge", window_controller)
    browser.page().setWebChannel(channel)
    
    # Lock window to fixed size - cannot be resized
    fixed_width = 1788
    fixed_height = 1500
    browser.setFixedSize(fixed_width, fixed_height)
    
    # Set rounded corners on frameless window
    corner_radius = 24
    path = QPainterPath()
    path.addRoundedRect(0, 0, fixed_width, fixed_height, corner_radius, corner_radius)
    mask = QRegion(path.toFillPolygon().toPolygon())
    browser.setMask(mask)
    
    # Load the local server URL (always use localhost for browser, even if server binds to 0.0.0.0)
    browser_host = "localhost" if WEBSOCKET_HOST == "0.0.0.0" else WEBSOCKET_HOST
    url = f"http://{browser_host}:{WEBSOCKET_PORT}"
    browser.load(QUrl(url))
    
    # Show the window and start the application
    browser.show()
    
    # Run the application
    exit_code = app.exec_()
    
    # Clean up UPnP port forwarding on exit
    if upnp_success:
        print(f"[UPnP] Cleaning up port forwarding...")
        remove_upnp_port_forward(WEBSOCKET_PORT)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


