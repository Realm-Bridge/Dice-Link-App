"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup.
Uses HTML/CSS rendered via QWebEngineView for consistent styling with main window.
Uses identical architecture to main.py - DraggableWebEngineView as the window itself.
"""

from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from pathlib import Path

from vtt_web import DraggableWebEngineView
from window_controller import WindowController

# Resolve the directory of this file
DICE_LINK_DIR = Path(__file__).resolve().parent


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
        self.login_successful = False
        
        # Ensure page is initialized (same as main.py line 157)
        self.setPage(self.page())
        
        # Enable transparent background for rounded corners (same as main.py line 160)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set up window controller for frameless window control (same as main.py lines 162-163)
        self.window_controller = WindowController(self, self)
        
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
    
    def exec(self) -> bool:
        """Show dialog and return True if login was successful."""
        self.show()
        return self.login_successful
