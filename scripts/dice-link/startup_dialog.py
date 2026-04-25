"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup
Uses HTML/CSS-based UI served from the FastAPI server, matching the main DLA window approach.
"""

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import pyqtSignal, QUrl, Qt
from PyQt6.QtGui import QIcon
from pathlib import Path

# Resolve the directory of this file
DICE_LINK_DIR = Path(__file__).resolve().parent


class StartupDialog(QMainWindow):
    """
    Initial login dialog shown on application startup.
    Uses HTML/CSS-based UI served from the FastAPI server.
    """
    
    # Signal emitted when user successfully connects
    connect_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username
    
    def __init__(self, server_port: int = 8765):
        super().__init__()
        
        self.server_port = server_port
        self.login_successful = False
        
        # Set up frameless window like main DLA window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Dice Link Login")
        self.setFixedSize(450, 520)
        
        # Set window icon for taskbar branding
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background_small.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        
        # Enable transparent background for rounded corners
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Create web engine view
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # Set up web channel for JavaScript-to-Python communication
        # Pass self twice to match main.py pattern: WindowController(browser, browser)
        from window_controller import WindowController
        self.window_controller = WindowController(self, self)
        channel = QWebChannel()
        channel.registerObject("pyqtBridge", self.window_controller)
        self.web_view.page().setWebChannel(channel)
        
        # Load the startup page from the server
        startup_url = f"http://localhost:{server_port}/startup"
        self.web_view.load(QUrl(startup_url))
    
    def exec(self) -> bool:
        """Show dialog and return True if login was successful."""
        self.show()
        return self.login_successful
    
    def on_login_success(self, connection_data: dict):
        """Called when login is successful."""
        self.login_successful = True
        self.connection_data = connection_data
        self.close()
