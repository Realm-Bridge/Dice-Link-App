"""Dice Link - Physical dice rolling companion for Foundry VTT"""

import threading
import time
import uvicorn
import sys
import os
import json
import socket
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QWidget, QSizePolicy
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QFontDatabase, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, Qt, QObject, pyqtSlot, pyqtSignal, QPoint, QEvent, QTimer, QEventLoop
from PyQt6.QtWebChannel import QWebChannel
# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, PHONE_CAMERA_PORT, APP_NAME, DEBUG, CONNECTION_METHOD
from debug import log_startup, log_server, log_drag_start, log_drag_move, log_drag_end, log_vtt, log_connection_monitor, log_dpi
from bridge_state import set_bridge
from custom_window import CustomWindow, CustomTitleBar, ResizeGrip
from vtt_validator import VTTValidator
from dialogs import ConnectionDialog
from dla_bridge import DLABridge
from vtt_web import VTTWebPage, VTTWebView, VTTPopupView, DraggableWebEngineView
from vtt_windows import VTTPopupWindow, VTTViewingWindow
from window_controller import WindowController
from startup_dialog import StartupDialog










def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def setup_phone_camera_certs():
    """Download local-ip.co certs for phone camera HTTPS. Returns (cert_path, key_path) or (None, None)."""
    certs_dir = DICE_LINK_DIR / "certs"
    certs_dir.mkdir(exist_ok=True)
    cert_file = certs_dir / "local-ip.pem"
    key_file = certs_dir / "local-ip.key"
    if cert_file.exists() and key_file.exists():
        return cert_file, key_file
    try:
        log_server("Downloading local-ip.co certs for phone camera...")
        with urllib.request.urlopen("http://local-ip.co/cert/server.pem", timeout=10) as r:
            server_pem = r.read()
        with urllib.request.urlopen("http://local-ip.co/cert/chain.pem", timeout=10) as r:
            chain_pem = r.read()
        cert_file.write_bytes(server_pem + b'\n' + chain_pem)
        with urllib.request.urlopen("http://local-ip.co/cert/server.key", timeout=10) as r:
            key_file.write_bytes(r.read())
        log_server("Phone camera certs ready")
        return cert_file, key_file
    except Exception as e:
        log_server(f"Could not download phone camera certs: {e}")
        return None, None


def run_phone_camera_server(cert_file, key_file):
    """HTTPS reverse proxy for phone camera — gives the phone a secure context for getUserMedia."""
    import ssl
    import http.server

    backend = f"http://127.0.0.1:{WEBSOCKET_PORT}"

    class ProxyHandler(http.server.BaseHTTPRequestHandler):
        def _proxy(self, method, body=None):
            try:
                headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in ('host', 'content-length')}
                req = urllib.request.Request(backend + self.path, data=body,
                                             headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_body = resp.read()
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp_body)
            except Exception as e:
                log_server(f"Phone camera proxy error: {e}")
                self.send_response(502)
                self.end_headers()

        def do_GET(self):
            self._proxy('GET')

        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length else None
            self._proxy('POST', body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def log_message(self, format, *args):
            pass

    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert_file), str(key_file))
        server = http.server.HTTPServer(('0.0.0.0', PHONE_CAMERA_PORT), ProxyHandler)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        log_server(f"Phone camera HTTPS proxy ready on port {PHONE_CAMERA_PORT}")
        server.serve_forever()
    except Exception as e:
        log_server(f"Phone camera HTTPS server failed to start: {e}")


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
    
    log_server(f"Connection method: QWebChannel (DLC runs inside embedded Foundry browser)")
    
    # Start the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Start HTTPS server for phone camera
    cert_file, key_file = setup_phone_camera_certs()
    if cert_file and key_file:
        phone_server_thread = threading.Thread(target=run_phone_camera_server, args=(cert_file, key_file), daemon=True)
        phone_server_thread.start()
    else:
        log_server("Phone camera HTTPS server not started — cert download failed")

    # Give the servers a moment to start
    time.sleep(1.5)
    
    # Create and display the PyQt6 window
    app = QApplication(sys.argv)
    
    # Show StartupDialog first
    startup_dialog = StartupDialog(server_port=WEBSOCKET_PORT)
    
    # Track if user connected successfully
    user_connected = False
    
    def on_connect_success(vtt_type, vtt_address, username):
        nonlocal user_connected
        user_connected = True
        log_server(f"User connected through StartupDialog: {vtt_type} at {vtt_address}")
        startup_dialog.close()
        startup_dialog.deleteLater()
    
    startup_dialog.connect_successful.connect(on_connect_success)
    startup_dialog.show()
    
    # Wait for dialog to close
    loop = QEventLoop()
    startup_dialog.destroyed.connect(loop.quit)
    loop.exec()
    
    if not user_connected:
        log_server("Startup cancelled by user")
        sys.exit(0)
    
    log_server("Proceeding with main application")
    
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
    logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background_small.ico"
    if logo_path.exists():
        browser.setWindowIcon(QIcon(str(logo_path)))
    
    # Set up web channel for JavaScript-to-Python communication
    channel = QWebChannel()
    channel.registerObject("pyqtBridge", window_controller)
    browser.page().setWebChannel(channel)
    
    # Resizable window — zoom tracks window width relative to designed width
    browser._designed_width = 1788
    browser._designed_height = 1500
    browser.setMinimumSize(400, 336)

    from core.storage import load_window_size, save_window_size
    screen_rect = app.primaryScreen().availableGeometry()
    saved_size = load_window_size()
    if saved_size:
        browser.resize(saved_size[0], saved_size[1])
    else:
        initial_width = int(screen_rect.width() * 0.4)
        initial_height = int(initial_width * 1500 / 1788)
        browser.resize(initial_width, initial_height)

    def update_dpi_scaling():
        screen = browser.screen()
        dpr = screen.devicePixelRatio() if screen else 1.0
        if browser._designed_width and browser.width() > 0:
            browser.setZoomFactor(browser.width() / browser._designed_width)
        log_dpi(f"Device pixel ratio: {dpr}")

    screen = browser.screen()
    if screen:
        screen.logicalDotsPerInchChanged.connect(update_dpi_scaling)
        screen.geometryChanged.connect(update_dpi_scaling)

    def save_size_on_quit():
        save_window_size(browser.width(), browser.height())

    app.aboutToQuit.connect(save_size_on_quit)

    # Load the local server URL (always use localhost for browser, even if server binds to 0.0.0.0)
    browser_host = "localhost" if WEBSOCKET_HOST == "0.0.0.0" else WEBSOCKET_HOST
    url = f"http://{browser_host}:{WEBSOCKET_PORT}"
    browser.load(QUrl(url))

    # Show the window and start the application
    browser.show()
    log_server(f"Main window shown — pos: {browser.pos()}, size: {browser.size()}, visible: {browser.isVisible()}")

    # Run the application
    exit_code = app.exec()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


