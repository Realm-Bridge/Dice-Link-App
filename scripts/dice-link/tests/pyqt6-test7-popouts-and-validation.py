"""
PyQt6 Test 7: Pop-out Windows and VTT Validation

Tests:
1. VTT Validation - Check if URL is actually a Foundry server
2. Pop-out Windows - Allow Foundry pop-outs, block external navigation
3. Same-origin policy - Foundry URLs allowed, external URLs blocked

This ensures users can use normal Foundry functionality while preventing
malicious navigation.
"""

import sys
import os
from urllib.parse import urlparse
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit, QSplitter
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class FoundryValidator:
    """Validates if a URL points to a Foundry VTT server"""
    
    @staticmethod
    def validate_foundry_url(url: str, callback):
        """
        Check if URL is a valid Foundry VTT server.
        
        Foundry indicators:
        - Page title contains "Foundry Virtual Tabletop"
        - Has /api/status endpoint
        - Returns specific HTML structure
        """
        # We'll do a simple check by looking for Foundry-specific API
        import urllib.request
        import urllib.error
        
        try:
            # Try the /api/status endpoint (Foundry v9+)
            api_url = url.rstrip('/') + '/api/status'
            req = urllib.request.Request(api_url, headers={'User-Agent': 'DLA-Validator/1.0'})
            
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = response.read().decode('utf-8')
                    # Foundry returns JSON with specific fields
                    try:
                        status = json.loads(data)
                        if 'active' in status or 'users' in status:
                            callback(True, "Foundry API status endpoint found", status)
                            return
                    except json.JSONDecodeError:
                        pass
            except urllib.error.HTTPError as e:
                # 404 is expected if not Foundry, but other errors might indicate it's there
                if e.code == 403:
                    # Forbidden could mean it's Foundry but requires auth
                    callback(True, "Foundry detected (API requires authentication)", None)
                    return
            
            # Fallback: Try loading the main page and checking for Foundry markers
            req = urllib.request.Request(url, headers={'User-Agent': 'DLA-Validator/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Check for Foundry-specific markers
                foundry_markers = [
                    'Foundry Virtual Tabletop',
                    'foundryvtt',
                    'game.ready',
                    'FoundryVTT'
                ]
                
                for marker in foundry_markers:
                    if marker.lower() in html.lower():
                        callback(True, f"Foundry marker found: '{marker}'", None)
                        return
                
                # Not Foundry
                callback(False, "No Foundry markers found in page", None)
                
        except urllib.error.URLError as e:
            callback(False, f"Connection failed: {e.reason}", None)
        except Exception as e:
            callback(False, f"Validation error: {str(e)}", None)


class FoundryWebPage(QWebEnginePage):
    """Custom web page that handles pop-outs and navigation"""
    
    def __init__(self, profile, allowed_origin, log_callback, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin  # e.g., "http://83.105.151.227:30000"
        self.log = log_callback
        self.popup_windows = []  # Keep references to prevent garbage collection
        
    def is_same_origin(self, url: QUrl) -> bool:
        """Check if URL is same origin as allowed Foundry server"""
        url_str = url.toString()
        parsed_new = urlparse(url_str)
        parsed_allowed = urlparse(self.allowed_origin)
        
        # Same origin = same scheme + host + port
        same = (parsed_new.scheme == parsed_allowed.scheme and 
                parsed_new.netloc == parsed_allowed.netloc)
        
        self.log(f"Origin check: {url_str}")
        self.log(f"  Allowed: {self.allowed_origin}")
        self.log(f"  Same origin: {same}")
        
        return same
    
    def createWindow(self, window_type):
        """
        Handle requests to open new windows (pop-outs).
        
        This is called when:
        - JavaScript uses window.open()
        - User clicks a link with target="_blank"
        - Foundry's pop-out feature is used
        """
        self.log(f"\n--- POPUP REQUEST ---")
        self.log(f"Window type: {window_type}")
        
        # Create a new window for same-origin requests
        # We'll check the URL in acceptNavigationRequest
        popup_page = FoundryPopupPage(self.profile(), self.allowed_origin, self.log)
        
        # Create a window to hold the popup
        popup_window = PopupWindow(popup_page, self.log)
        self.popup_windows.append(popup_window)  # Keep reference
        
        self.log("Popup window created - waiting for navigation request")
        return popup_page
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """
        Intercept navigation requests.
        
        Allow: Same-origin Foundry URLs
        Block: External URLs
        """
        self.log(f"\n--- NAVIGATION REQUEST ---")
        self.log(f"URL: {url.toString()}")
        self.log(f"Type: {nav_type}")
        self.log(f"Main frame: {is_main_frame}")
        
        if self.is_same_origin(url):
            self.log("ALLOWED: Same origin")
            return True
        else:
            # Check if it's a special URL we should allow
            url_str = url.toString()
            
            # Allow about:blank (used for some popups initially)
            if url_str == 'about:blank':
                self.log("ALLOWED: about:blank")
                return True
            
            # Allow javascript: URLs (used by Foundry)
            if url_str.startswith('javascript:'):
                self.log("ALLOWED: javascript: URL")
                return True
            
            # Block external navigation
            self.log("BLOCKED: External URL")
            return False


class FoundryPopupPage(QWebEnginePage):
    """Page for popup windows with same navigation restrictions"""
    
    def __init__(self, profile, allowed_origin, log_callback, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin
        self.log = log_callback
        
    def is_same_origin(self, url: QUrl) -> bool:
        url_str = url.toString()
        parsed_new = urlparse(url_str)
        parsed_allowed = urlparse(self.allowed_origin)
        return (parsed_new.scheme == parsed_allowed.scheme and 
                parsed_new.netloc == parsed_allowed.netloc)
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        self.log(f"[POPUP] Navigation: {url.toString()}")
        
        if self.is_same_origin(url):
            self.log("[POPUP] ALLOWED: Same origin")
            return True
        
        url_str = url.toString()
        if url_str == 'about:blank' or url_str.startswith('javascript:'):
            return True
            
        self.log("[POPUP] BLOCKED: External URL")
        return False


class PopupWindow(QMainWindow):
    """Window container for Foundry pop-outs"""
    
    def __init__(self, page, log_callback):
        super().__init__()
        self.log = log_callback
        
        self.setWindowTitle("Foundry Pop-out")
        self.resize(600, 400)
        
        self.browser = QWebEngineView()
        self.browser.setPage(page)
        self.setCentralWidget(self.browser)
        
        # Connect to show when content loads
        page.loadFinished.connect(self.on_load_finished)
        
    def on_load_finished(self, ok):
        if ok:
            self.log("[POPUP] Content loaded - showing window")
            self.show()
        else:
            self.log("[POPUP] Load failed")


class TestWindow(QMainWindow):
    def __init__(self, url: str):
        super().__init__()
        self.target_url = url
        self.allowed_origin = url.rstrip('/')
        
        self.setWindowTitle("PyQt6 Test 7: Pop-outs and VTT Validation")
        self.resize(1400, 900)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Splitter for browser and controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Browser
        self.setup_browser()
        splitter.addWidget(self.browser)
        
        # Control panel
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        splitter.addWidget(control_panel)
        
        # Title
        title = QLabel("Pop-out & Validation Tests")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_layout.addWidget(title)
        
        # URL input for validation
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to validate...")
        self.url_input.setText(url)
        url_layout.addWidget(self.url_input)
        control_layout.addLayout(url_layout)
        
        # Test buttons
        self.btn_validate = QPushButton("Test 1: Validate Foundry URL")
        self.btn_validate.clicked.connect(self.test_validate)
        control_layout.addWidget(self.btn_validate)
        
        self.btn_load = QPushButton("Test 2: Load VTT")
        self.btn_load.clicked.connect(self.test_load)
        control_layout.addWidget(self.btn_load)
        
        self.btn_popout = QPushButton("Test 3: Trigger Foundry Pop-out")
        self.btn_popout.clicked.connect(self.test_popout)
        control_layout.addWidget(self.btn_popout)
        
        self.btn_external = QPushButton("Test 4: Try External Navigation (should block)")
        self.btn_external.clicked.connect(self.test_external_blocked)
        control_layout.addWidget(self.btn_external)
        
        self.btn_summary = QPushButton("Show Test Summary")
        self.btn_summary.clicked.connect(self.show_summary)
        control_layout.addWidget(self.btn_summary)
        
        # Log output
        log_label = QLabel("Log Output:")
        control_layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: monospace; font-size: 11px;")
        control_layout.addWidget(self.log_output)
        
        # Set splitter sizes
        splitter.setSizes([900, 500])
        
        # Test tracking
        self.test_results = {}
        
        self.log("Test 7: Pop-outs and VTT Validation")
        self.log(f"Target URL: {url}")
        self.log("Ready for testing.\n")
        
    def setup_browser(self):
        """Set up browser with custom page that handles popups"""
        profile = QWebEngineProfile.defaultProfile()
        
        self.browser = QWebEngineView()
        self.custom_page = FoundryWebPage(profile, self.allowed_origin, self.log, self.browser)
        self.browser.setPage(self.custom_page)
        
    def log(self, message: str):
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )
        print(message)
        
    def test_validate(self):
        """Test 1: Validate if URL is Foundry"""
        self.log("\n--- TEST 1: Validate Foundry URL ---")
        url = self.url_input.text().strip()
        
        if not url:
            self.log("ERROR: No URL entered")
            return
            
        self.log(f"Validating: {url}")
        self.log("Checking for Foundry markers...")
        
        def on_result(is_foundry, message, data):
            self.log(f"\nValidation result:")
            self.log(f"  Is Foundry: {is_foundry}")
            self.log(f"  Message: {message}")
            if data:
                self.log(f"  API Data: {json.dumps(data, indent=2)}")
            
            if is_foundry:
                self.log("\nPASS: URL is a valid Foundry VTT server")
                self.test_results['validate'] = True
            else:
                self.log("\nFAIL: URL does not appear to be Foundry VTT")
                self.test_results['validate'] = False
        
        # Run validation in thread to avoid blocking UI
        import threading
        thread = threading.Thread(target=lambda: FoundryValidator.validate_foundry_url(url, on_result))
        thread.start()
        
    def test_load(self):
        """Test 2: Load the VTT"""
        self.log("\n--- TEST 2: Load VTT ---")
        url = self.url_input.text().strip()
        
        self.log(f"Loading: {url}")
        self.browser.setUrl(QUrl(url))
        
        self.browser.loadFinished.connect(self.on_load_finished)
        
    def on_load_finished(self, ok):
        if ok:
            self.log("VTT loaded successfully")
            self.log("PASS: VTT page loaded")
            self.test_results['load'] = True
        else:
            self.log("FAIL: VTT failed to load")
            self.test_results['load'] = False
            
    def test_popout(self):
        """Test 3: Try to trigger Foundry's pop-out feature"""
        self.log("\n--- TEST 3: Foundry Pop-out ---")
        self.log("Attempting to trigger pop-out via JavaScript...")
        self.log("(If Foundry v14 is loaded, this should open a pop-out window)")
        
        # Try to pop out the chat log - a common Foundry pop-out
        popout_script = """
        (function() {
            // Try to find and pop out the chat log
            if (typeof ui !== 'undefined' && ui.chat) {
                try {
                    ui.chat.renderPopout();
                    return 'Pop-out triggered for chat';
                } catch(e) {
                    return 'Error triggering pop-out: ' + e.message;
                }
            }
            
            // Alternative: try to pop out sidebar
            if (typeof ui !== 'undefined' && ui.sidebar) {
                try {
                    // Find first tab and pop it out
                    var tabs = document.querySelectorAll('.sidebar-tab');
                    if (tabs.length > 0) {
                        return 'Sidebar tabs found. Use Foundry UI to test pop-out.';
                    }
                } catch(e) {
                    return 'Error: ' + e.message;
                }
            }
            
            // Check if we're on login page
            if (document.querySelector('form[id="join-game"]')) {
                return 'On login page - join a world first to test pop-outs';
            }
            
            return 'Could not find Foundry UI elements. Make sure you are in a game session.';
        })();
        """
        
        def on_result(result):
            self.log(f"Pop-out result: {result}")
            if 'triggered' in str(result).lower() or 'found' in str(result).lower():
                self.log("Check if a pop-out window appeared.")
                self.log("If yes: PASS - Pop-outs work correctly")
            else:
                self.log("Manual test required: Right-click a sheet and select 'Pop Out'")
        
        self.browser.page().runJavaScript(popout_script, on_result)
        
    def test_external_blocked(self):
        """Test 4: Verify external navigation is blocked"""
        self.log("\n--- TEST 4: External Navigation Block ---")
        self.log("Attempting to navigate to external URL (should be blocked)...")
        
        # Try to navigate to an external site
        external_script = """
        (function() {
            try {
                window.location.href = 'https://www.google.com';
                return 'Navigation attempted';
            } catch(e) {
                return 'Navigation blocked by error: ' + e.message;
            }
        })();
        """
        
        def on_result(result):
            self.log(f"Result: {result}")
            self.log("If the page did NOT navigate to Google, the block is working.")
            self.log("Check the log above for 'BLOCKED: External URL' message.")
            
        self.browser.page().runJavaScript(external_script, on_result)
        
        # Also try window.open
        self.log("\nAlso testing window.open to external site...")
        
        popup_script = """
        (function() {
            try {
                var win = window.open('https://www.google.com', '_blank');
                return win ? 'window.open returned a window object' : 'window.open returned null (blocked)';
            } catch(e) {
                return 'window.open blocked: ' + e.message;
            }
        })();
        """
        
        def on_popup_result(result):
            self.log(f"window.open result: {result}")
            if 'blocked' in str(result).lower() or 'null' in str(result).lower():
                self.log("PASS: External popup blocked")
                self.test_results['external_blocked'] = True
            else:
                self.log("Check if external window opened - should have been blocked")
        
        self.browser.page().runJavaScript(popup_script, on_popup_result)
        
    def show_summary(self):
        """Show summary of all tests"""
        self.log("\n" + "="*50)
        self.log("TEST SUMMARY")
        self.log("="*50)
        
        tests = [
            ('validate', 'Foundry URL Validation'),
            ('load', 'VTT Page Load'),
            ('popout', 'Pop-out Windows'),
            ('external_blocked', 'External Navigation Block')
        ]
        
        for key, name in tests:
            if key in self.test_results:
                status = "PASS" if self.test_results[key] else "FAIL"
                self.log(f"{name}: {status}")
            else:
                self.log(f"{name}: NOT TESTED")
        
        self.log("="*50)


def main():
    if len(sys.argv) < 2:
        print("Usage: python pyqt6-test7-popouts-and-validation.py <URL>")
        print("Example: python pyqt6-test7-popouts-and-validation.py http://localhost:30000")
        sys.exit(1)
    
    url = sys.argv[1]
    
    app = QApplication(sys.argv)
    window = TestWindow(url)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
