"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup.
Uses HTML/CSS rendered via QWebEngineView for consistent styling with main window.
"""

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from pathlib import Path

# Resolve the directory of this file
DICE_LINK_DIR = Path(__file__).resolve().parent


class StartupDialog(QMainWindow):
    """
    Initial login dialog shown on application startup.
    Uses HTML/CSS rendered via QWebEngineView for consistent styling.
    """
    
    # Signal emitted when user successfully connects
    connect_successful = pyqtSignal(str, str, str)  # vtt_type, vtt_address, username
    
    def __init__(self, server_port: int = 8765):
        super().__init__()
        
        self.server_port = server_port
        self.login_successful = False
        
        # Frameless window like main DLA window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.setWindowTitle("Dice Link Login")
        self.setFixedSize(550, 650)
        
        # Set window icon
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background_small.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Web view to render HTML
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Set up web channel for JavaScript-to-Python communication
        # Pass self twice to match main.py pattern: WindowController(browser, browser)
        from window_controller import WindowController
        self.window_controller = WindowController(self, self)
        channel = QWebChannel()
        channel.registerObject("pyqtBridge", self.window_controller)
        self.web_view.page().setWebChannel(channel)
        
        # Load the startup HTML page from the server
        self.web_view.setUrl(QUrl(f"http://localhost:{self.server_port}/startup"))
    
    def exec(self) -> bool:
        """Show dialog and return True if login was successful."""
        self.show()
        return self.login_successful
