"""
PyQt6 Test 9: Working Pop-out Windows

Tests that Foundry pop-out windows work correctly.
Uses Qt6's proper openIn() method for handling new window requests.

Usage:
    python pyqt6-test9-popouts-working.py http://localhost:30000
    python pyqt6-test9-popouts-working.py http://83.105.151.227:30000
"""

import sys
from urllib.parse import urlparse

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSplitter
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings


class PopoutWindow(QMainWindow):
    """Separate window for Foundry pop-outs (character sheets, etc.)"""
    
    def __init__(self, main_window, log_func):
        super().__init__()
        self.main_window = main_window
        self.log = log_func
        self.setWindowTitle("Foundry Pop-out")
        self.resize(600, 700)
        
        # Create the web view for this popup
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        
        # Use same settings as main window
        settings = self.browser.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        
        # Handle popups from this popup too (nested popups)
        self.browser.page().newWindowRequested.connect(self.handle_nested_popup)
        
        self.log("[POPUP WINDOW] Created new popup window")
    
    def get_page(self):
        """Return the page for openIn()"""
        return self.browser.page()
    
    def handle_nested_popup(self, request):
        """Handle popups from within popups"""
        self.log(f"[NESTED POPUP] Request from popup: {request.requestedUrl().toString()}")
        # Create another popup window
        nested = PopoutWindow(self.main_window, self.log)
        request.openIn(nested.get_page())
        nested.show()
        # Keep reference
        if not hasattr(self.main_window, 'popup_windows'):
            self.main_window.popup_windows = []
        self.main_window.popup_windows.append(nested)


class MainWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.base_origin = self.get_origin(url)
        self.popup_windows = []  # Keep references to popup windows
        
        self.setWindowTitle("PyQt6 Test 9: Working Pop-outs")
        self.resize(1400, 900)
        
        # Main widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Splitter for browser and controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Browser
        self.browser = QWebEngineView()
        splitter.addWidget(self.browser)
        
        # Control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        splitter.addWidget(control_panel)
        
        # Title
        title = QLabel("Pop-out Window Tests")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_layout.addWidget(title)
        
        # Test buttons
        self.btn_load = QPushButton("Test 1: Load VTT")
        self.btn_load.clicked.connect(self.test_load)
        control_layout.addWidget(self.btn_load)
        
        self.btn_info = QPushButton("Test 2: Show Pop-out Info")
        self.btn_info.clicked.connect(self.test_info)
        control_layout.addWidget(self.btn_info)
        
        self.btn_count = QPushButton("Test 3: Count Open Pop-outs")
        self.btn_count.clicked.connect(self.test_count)
        control_layout.addWidget(self.btn_count)
        
        self.btn_close_all = QPushButton("Test 4: Close All Pop-outs")
        self.btn_close_all.clicked.connect(self.test_close_all)
        control_layout.addWidget(self.btn_close_all)
        
        # Log output
        log_label = QLabel("Log Output:")
        control_layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: monospace; font-size: 11px;")
        control_layout.addWidget(self.log_output)
        
        # Set splitter sizes
        splitter.setSizes([1000, 400])
        
        # Configure browser settings
        self.setup_browser()
        
        # Log startup
        self.log("Pop-out Window Test Started")
        self.log(f"URL: {url}")
        self.log(f"Base origin: {self.base_origin}")
        self.log("")
        self.log("INSTRUCTIONS:")
        self.log("1. Click 'Test 1: Load VTT' to load Foundry")
        self.log("2. Join a world and open a character sheet")
        self.log("3. Right-click the sheet header and select 'Pop Out'")
        self.log("4. The sheet should open in a new window")
        self.log("")
    
    def setup_browser(self):
        """Configure browser settings for Foundry"""
        settings = self.browser.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        
        # CRITICAL: Allow JavaScript to open windows (needed for pop-outs)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        
        # Connect the new window request handler
        self.browser.page().newWindowRequested.connect(self.handle_new_window)
        
        self.log("[SETUP] Browser configured with JavascriptCanOpenWindows = True")
        self.log("[SETUP] newWindowRequested signal connected")
    
    def get_origin(self, url):
        """Extract origin from URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def is_same_origin(self, url):
        """Check if URL is same origin as base VTT"""
        if isinstance(url, QUrl):
            url = url.toString()
        return self.get_origin(url) == self.base_origin
    
    def handle_new_window(self, request):
        """Handle new window requests from Foundry (pop-outs)"""
        requested_url = request.requestedUrl().toString()
        self.log(f"\n--- NEW WINDOW REQUEST ---")
        self.log(f"URL: {requested_url}")
        self.log(f"User initiated: {request.isUserInitiated()}")
        self.log(f"Destination type: {request.destination()}")
        
        # Check if same origin
        if self.is_same_origin(requested_url):
            self.log("[DECISION] ALLOWED - Same origin pop-out")
            
            # Create a new popup window
            popup = PopoutWindow(self, self.log)
            
            # Use Qt6's openIn() method - this is the correct way
            request.openIn(popup.get_page())
            
            # Show the popup window
            popup.show()
            
            # Keep reference to prevent garbage collection
            self.popup_windows.append(popup)
            
            self.log(f"[SUCCESS] Pop-out window created and shown")
            self.log(f"[INFO] Total open pop-outs: {len(self.popup_windows)}")
        else:
            self.log("[DECISION] BLOCKED - External origin")
            self.log(f"  Base origin: {self.base_origin}")
            self.log(f"  Requested origin: {self.get_origin(requested_url)}")
            # Don't call openIn() - this blocks the request
    
    def log(self, message):
        """Add message to log output"""
        self.log_output.append(message)
        print(message)
    
    def test_load(self):
        """Test 1: Load VTT"""
        self.log("\n--- TEST 1: Load VTT ---")
        self.browser.setUrl(QUrl(self.url))
        self.log(f"Loading: {self.url}")
        self.log("Wait for page to fully load before testing pop-outs")
    
    def test_info(self):
        """Test 2: Show pop-out information"""
        self.log("\n--- TEST 2: Pop-out Info ---")
        self.log(f"JavascriptCanOpenWindows setting is enabled")
        self.log(f"newWindowRequested signal is connected")
        self.log(f"Same-origin pop-outs: ALLOWED")
        self.log(f"External pop-outs: BLOCKED")
        self.log("")
        self.log("To test pop-outs manually:")
        self.log("1. Join a world in Foundry")
        self.log("2. Open a character sheet or item")
        self.log("3. Right-click the sheet header")
        self.log("4. Select 'Pop Out' from the menu")
        self.log("5. A new window should appear")
    
    def test_count(self):
        """Test 3: Count open pop-outs"""
        self.log("\n--- TEST 3: Count Pop-outs ---")
        # Clean up closed windows
        self.popup_windows = [w for w in self.popup_windows if w.isVisible()]
        self.log(f"Currently open pop-out windows: {len(self.popup_windows)}")
        
        for i, popup in enumerate(self.popup_windows):
            self.log(f"  Pop-out {i+1}: {popup.windowTitle()}")
    
    def test_close_all(self):
        """Test 4: Close all pop-outs"""
        self.log("\n--- TEST 4: Close All Pop-outs ---")
        count = len(self.popup_windows)
        for popup in self.popup_windows:
            popup.close()
        self.popup_windows.clear()
        self.log(f"Closed {count} pop-out window(s)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python pyqt6-test9-popouts-working.py <URL>")
        print("Example: python pyqt6-test9-popouts-working.py http://localhost:30000")
        sys.exit(1)
    
    url = sys.argv[1]
    
    app = QApplication(sys.argv)
    window = MainWindow(url)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
