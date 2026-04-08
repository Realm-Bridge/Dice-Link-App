"""Dice Link - Physical dice rolling companion for Foundry VTT"""

import threading
import time
import uvicorn
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG


def run_server():
    """Run the FastAPI server in a background thread"""
    uvicorn.run(
        "app:app",
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
    
    # Set window properties
    browser.setWindowTitle(APP_NAME)
    browser.resize(1200, 800)
    
    # Set zoom level to make text much larger (2.0 = 200% of normal size)
    browser.setZoomFactor(2.0)
    
    # Load the local server URL
    url = f"http://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
    browser.load(QUrl(url))
    
    # Show the window and start the application
    browser.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


