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
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot, QWebChannel

# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG


class WindowController(QObject):
    """Handles window control commands from JavaScript"""
    
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
    
    @pyqtSlot()
    def minimize(self):
        """Minimize the window"""
        self.browser.showMinimized()
    
    @pyqtSlot()
    def maximize(self):
        """Maximize the window (toggle for frameless)"""
        if self.browser.isMaximized():
            self.browser.showNormal()
        else:
            self.browser.showMaximized()
    
    @pyqtSlot()
    def close(self):
        """Close the application"""
        self.browser.close()


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
    print(f"DLC module should connect to ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws/dlc")
    
    # Start the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1.5)
    
    # Create and display the PyQt5 window
    app = QApplication(sys.argv)
    
    # Create a web view widget
    browser = QWebEngineView()
    
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
    
    # Load the local server URL
    url = f"http://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
    browser.load(QUrl(url))
    
    # Show the window and start the application
    browser.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


