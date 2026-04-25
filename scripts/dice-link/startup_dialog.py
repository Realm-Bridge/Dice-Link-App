"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup.
Uses HTML/CSS rendered via QWebEngineView for consistent styling with main window.
Uses identical architecture to main.py - DraggableWebEngineView as the window itself.
"""

from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QIcon
from pathlib import Path

from vtt_web import DraggableWebEngineView
from window_controller import WindowController

# Resolve the directory of this file
DICE_LINK_DIR = Path(__file__).resolve().parent


class StartupWindowController(WindowController):
    """
    Extends WindowController with login functionality for the startup dialog.
    Inherits: minimize(), close(), startDrag(), doDrag() from WindowController.
    Adds: login() for form submission.
    Re-declares inherited methods with @pyqtSlot for JavaScript access.
    """
    
    # Signal emitted when user successfully logs in
    login_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username
    
    @pyqtSlot()
    def minimize(self):
        """Minimize the window."""
        print("[v0] minimize() called from JavaScript")
        super().minimize()
    
    @pyqtSlot()
    def close(self):
        """Close the window."""
        print("[v0] close() called from JavaScript")
        super().close()
    
    @pyqtSlot(int, int)
    def startDrag(self, pos_x: int, pos_y: int):
        """Start dragging the window."""
        print(f"[v0] startDrag({pos_x}, {pos_y}) called from JavaScript")
        super().startDrag(pos_x, pos_y)
    
    @pyqtSlot(int, int)
    def doDrag(self, pos_x: int, pos_y: int):
        """Continue dragging the window."""
        print(f"[v0] doDrag({pos_x}, {pos_y}) called from JavaScript")
        super().doDrag(pos_x, pos_y)
    
    @pyqtSlot(str, str, str, str)
    def login(self, vtt_type: str, vtt_address: str, username: str, password: str):
        """
        Called by JavaScript when user submits login form.
        Validates input and emits login_successful signal.
        """
        print(f"[v0] login({vtt_type}, {vtt_address}, {username}, {password}) called from JavaScript")
        if vtt_type and vtt_address and username and password:
            print("[v0] Login validation passed, emitting login_successful signal")
            self.login_successful.emit(vtt_type, vtt_address, username)


class StartupDialog(DraggableWebEngineView):
    """
    Initial login dialog shown on application startup.
    Uses HTML/CSS rendered via QWebEngineView for consistent styling.
    Uses identical architecture to main DLA window - DraggableWebEngineView as the window itself.
    """
    
    # Signal emitted when user successfully connects
    connect_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username
    
    def __init__(self, server_port: int = 8765):
        super().__init__()
        
        self.server_port = server_port
        
        # Ensure page is initialized (same as main.py line 157)
        self.setPage(self.page())
        
        # Enable transparent background for rounded corners (same as main.py line 160)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set up window controller for frameless window control (same as main.py lines 162-163)
        # Uses StartupWindowController which extends WindowController with login()
        self.window_controller = StartupWindowController(self, self)
        
        # Connect login signal to our connect_successful signal
        self.window_controller.login_successful.connect(self._on_login_successful)
        
        # Set window properties (same as main.py lines 165-166)
        self.setWindowTitle("Dice Link Login")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Set window icon (same as main.py lines 168-170)
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background_small.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        
        # Set up web channel for JavaScript-to-Python communication (same as main.py lines 172-174)
        channel = QWebChannel()
        channel.registerObject("pyqtBridge", self.window_controller)
        self.page().setWebChannel(channel)
        
        # Set fixed size for startup dialog
        self.setFixedSize(550, 650)
        
        # Load the startup HTML page from the server (same as main.py line 194)
        self.load(QUrl(f"http://localhost:{self.server_port}/startup"))
    
    def _on_login_successful(self, vtt_type: str, vtt_address: str, username: str):
        """Forward login success to connect_successful signal."""
        self.connect_successful.emit(vtt_type, vtt_address, username)
