"""
Realm Bridge / Dice Link - Startup Dialog Module
Initial login and VTT selection dialog shown on application startup
"""

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import pyqtSignal, QUrl
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
    
    def __init__(self, server_port: int = 8000):
        super().__init__()
        
        self.setWindowTitle("Dice Link Login")
        self.setFixedSize(450, 520)
        
        # Create web engine view
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # Load the startup page from the server
        startup_url = f"http://localhost:{server_port}/startup"
        self.web_view.load(QUrl(startup_url))
