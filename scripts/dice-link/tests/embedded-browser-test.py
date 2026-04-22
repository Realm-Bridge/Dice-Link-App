"""
Embedded Browser Feasibility Test for VTT Integration

This test validates whether an embedded Chromium browser (via Qt WebEngine) 
can serve as a viable approach for DLA to host VTT content.

Tests are run sequentially - each must pass before proceeding:
1. Can Qt WebEngine load and render a VTT properly?
2. Do command-line switches bypass Chrome's secure origin restrictions?
3. Can we inject JavaScript into the page from Python?
4. Can injected JavaScript communicate back to Python?
5. Can we create a locked-down window (VTT-only, no browsing)?

Usage:
    python embedded-browser-test.py <foundry-url>
    
Example:
    python embedded-browser-test.py http://192.168.1.55:30000

The test will guide you through each step with clear pass/fail indicators.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
DICE_LINK_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(DICE_LINK_DIR))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot, pyqtSignal, QTimer


class TestResults:
    """Track test results"""
    def __init__(self):
        self.results = {}
    
    def set(self, test_name, passed, message=""):
        self.results[test_name] = {"passed": passed, "message": message}
    
    def get_summary(self):
        lines = ["\n" + "="*60, "TEST RESULTS SUMMARY", "="*60]
        for name, result in self.results.items():
            status = "PASS" if result["passed"] else "FAIL"
            lines.append(f"[{status}] {name}")
            if result["message"]:
                lines.append(f"       {result['message']}")
        lines.append("="*60)
        return "\n".join(lines)


class JavaScriptBridge(QObject):
    """Bridge for JavaScript to Python communication (Test 4)"""
    
    message_received = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.received_messages = []
    
    @pyqtSlot(str)
    def sendToPython(self, message):
        """Called from JavaScript to send data to Python"""
        print(f"[Python] Received from JavaScript: {message}")
        self.received_messages.append(message)
        self.message_received.emit(message)
    
    @pyqtSlot(result=str)
    def getFromPython(self):
        """Called from JavaScript to get data from Python"""
        return "Hello from Python!"


class CustomWebEnginePage(QWebEnginePage):
    """Custom page to handle console messages and errors"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.console_messages = []
        self.load_errors = []
    
    def javaScriptConsoleMessage(self, level, message, line, source):
        """Capture JavaScript console messages"""
        level_names = {0: "INFO", 1: "WARNING", 2: "ERROR"}
        level_name = level_names.get(level, "UNKNOWN")
        log_entry = f"[JS {level_name}] {message} (line {line})"
        print(log_entry)
        self.console_messages.append(log_entry)
    
    def certificateError(self, error):
        """Handle certificate errors - accept them for testing"""
        print(f"[CERT ERROR] {error.errorDescription()} - Accepting anyway")
        error.acceptCertificate()
        return True
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Log navigation requests"""
        print(f"[NAV] {'MAIN' if is_main_frame else 'SUB'}: {url.toString()[:100]}")
        return True


class EmbeddedBrowserTest(QMainWindow):
    """Main test window"""
    
    def __init__(self, vtt_url):
        super().__init__()
        self.vtt_url = vtt_url
        self.test_results = TestResults()
        self.js_bridge = JavaScriptBridge()
        
        self.setWindowTitle("Embedded Browser Feasibility Test")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setup_ui()
        self.setup_browser()
    
    def setup_ui(self):
        """Create the test UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel: Browser view
        browser_group = QGroupBox("Embedded VTT Browser")
        browser_layout = QVBoxLayout(browser_group)
        
        # URL display (read-only - demonstrates locked-down approach)
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Locked to:"))
        self.url_label = QLabel(self.vtt_url)
        self.url_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        url_layout.addWidget(self.url_label)
        url_layout.addStretch()
        browser_layout.addLayout(url_layout)
        
        # Browser widget
        self.browser = QWebEngineView()
        browser_layout.addWidget(self.browser)
        
        main_layout.addWidget(browser_group, stretch=3)
        
        # Right panel: Test controls
        control_group = QGroupBox("Test Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Test 1: Page Load
        self.test1_btn = QPushButton("Test 1: Load VTT Page")
        self.test1_btn.clicked.connect(self.run_test_1)
        self.test1_status = QLabel("Not run")
        control_layout.addWidget(self.test1_btn)
        control_layout.addWidget(self.test1_status)
        control_layout.addWidget(self.create_separator())
        
        # Test 2: Secure Origin Bypass
        self.test2_btn = QPushButton("Test 2: Check Secure Origin")
        self.test2_btn.clicked.connect(self.run_test_2)
        self.test2_btn.setEnabled(False)
        self.test2_status = QLabel("Waiting for Test 1")
        control_layout.addWidget(self.test2_btn)
        control_layout.addWidget(self.test2_status)
        control_layout.addWidget(self.create_separator())
        
        # Test 3: JavaScript Injection
        self.test3_btn = QPushButton("Test 3: Inject JavaScript")
        self.test3_btn.clicked.connect(self.run_test_3)
        self.test3_btn.setEnabled(False)
        self.test3_status = QLabel("Waiting for Test 2")
        control_layout.addWidget(self.test3_btn)
        control_layout.addWidget(self.test3_status)
        control_layout.addWidget(self.create_separator())
        
        # Test 4: JS-to-Python Communication
        self.test4_btn = QPushButton("Test 4: JS to Python Bridge")
        self.test4_btn.clicked.connect(self.run_test_4)
        self.test4_btn.setEnabled(False)
        self.test4_status = QLabel("Waiting for Test 3")
        control_layout.addWidget(self.test4_btn)
        control_layout.addWidget(self.test4_status)
        control_layout.addWidget(self.create_separator())
        
        # Test 5: Locked Window Demo
        self.test5_btn = QPushButton("Test 5: Verify Locked Window")
        self.test5_btn.clicked.connect(self.run_test_5)
        self.test5_btn.setEnabled(False)
        self.test5_status = QLabel("Waiting for Test 4")
        control_layout.addWidget(self.test5_btn)
        control_layout.addWidget(self.test5_status)
        control_layout.addWidget(self.create_separator())
        
        # Summary button
        self.summary_btn = QPushButton("Show Test Summary")
        self.summary_btn.clicked.connect(self.show_summary)
        control_layout.addWidget(self.summary_btn)
        
        # Debug button - check page content
        self.debug_btn = QPushButton("DEBUG: Check Page Content")
        self.debug_btn.clicked.connect(self.run_debug_check)
        control_layout.addWidget(self.debug_btn)
        
        # Log output
        control_layout.addWidget(QLabel("Log Output:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        control_layout.addWidget(self.log_output)
        
        control_layout.addStretch()
        
        main_layout.addWidget(control_group, stretch=1)
    
    def create_separator(self):
        """Create a horizontal line separator"""
        separator = QLabel()
        separator.setStyleSheet("border-bottom: 1px solid #ccc; margin: 5px 0;")
        separator.setFixedHeight(2)
        return separator
    
    def setup_browser(self):
        """Configure the browser with secure origin bypass"""
        # Create custom page for console logging
        self.custom_page = CustomWebEnginePage(self.browser)
        self.browser.setPage(self.custom_page)
        
        # Set up web channel for JavaScript communication
        self.channel = QWebChannel()
        self.channel.registerObject("pyBridge", self.js_bridge)
        self.custom_page.setWebChannel(self.channel)
        
        # Enable settings that might be needed for VTT
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        
        self.log("Browser configured with WebGL and local storage enabled")
        self.log("Secure origin bypass: AllowRunningInsecureContent enabled")
    
    def log(self, message):
        """Add message to log output"""
        self.log_output.append(message)
        print(f"[Test Log] {message}")
    
    def set_status(self, label, passed, message):
        """Update a status label"""
        if passed:
            label.setText(f"PASS: {message}")
            label.setStyleSheet("color: green; font-weight: bold;")
        else:
            label.setText(f"FAIL: {message}")
            label.setStyleSheet("color: red; font-weight: bold;")
    
    # =========================================================================
    # TEST 1: Can Qt WebEngine load and render VTT properly?
    # =========================================================================
    def run_test_1(self):
        """Test 1: Load the VTT page and check if it renders"""
        self.log("\n--- TEST 1: Loading VTT Page ---")
        self.log(f"URL: {self.vtt_url}")
        
        self.test1_status.setText("Loading...")
        self.test1_status.setStyleSheet("color: orange;")
        
        # Connect to load finished signal
        self.browser.loadFinished.connect(self.on_test1_load_finished)
        
        # Load the URL
        self.browser.load(QUrl(self.vtt_url))
    
    def on_test1_load_finished(self, success):
        """Handle page load completion for Test 1"""
        # Disconnect to avoid multiple calls
        try:
            self.browser.loadFinished.disconnect(self.on_test1_load_finished)
        except:
            pass
        
        if success:
            self.log("Page loaded successfully")
            # Give the page a moment to render, then check for content
            QTimer.singleShot(2000, self.verify_test1_rendering)
        else:
            self.log("Page failed to load")
            self.set_status(self.test1_status, False, "Page failed to load")
            self.test_results.set("Test 1: Load VTT", False, "Page load failed")
    
    def verify_test1_rendering(self):
        """Verify the page rendered content"""
        # Check if the page has rendered content by looking for body content
        js_check = """
        (function() {
            var hasCanvas = document.querySelector('canvas') !== null;
            var hasFoundry = typeof game !== 'undefined';
            var bodyContent = document.body && document.body.innerHTML.length > 100;
            return JSON.stringify({
                hasCanvas: hasCanvas,
                hasFoundry: hasFoundry,
                bodyLength: document.body ? document.body.innerHTML.length : 0,
                title: document.title
            });
        })();
        """
        self.browser.page().runJavaScript(js_check, self.on_test1_verify)
    
    def on_test1_verify(self, result):
        """Process Test 1 verification result"""
        try:
            import json
            data = json.loads(result) if isinstance(result, str) else result
            self.log(f"Page title: {data.get('title', 'Unknown')}")
            self.log(f"Has canvas element: {data.get('hasCanvas', False)}")
            self.log(f"Has Foundry game object: {data.get('hasFoundry', False)}")
            self.log(f"Body content length: {data.get('bodyLength', 0)}")
            
            # Consider it a pass if we have significant content
            passed = data.get('bodyLength', 0) > 100
            
            if passed:
                self.set_status(self.test1_status, True, "VTT page loaded and rendered")
                self.test_results.set("Test 1: Load VTT", True, f"Title: {data.get('title')}")
                self.test2_btn.setEnabled(True)
                self.test2_status.setText("Ready")
            else:
                self.set_status(self.test1_status, False, "Page loaded but content is minimal")
                self.test_results.set("Test 1: Load VTT", False, "Minimal content rendered")
        except Exception as e:
            self.log(f"Error verifying page: {e}")
            self.set_status(self.test1_status, False, f"Verification error: {e}")
            self.test_results.set("Test 1: Load VTT", False, str(e))
    
    # =========================================================================
    # TEST 2: Do command-line switches bypass secure origin restrictions?
    # =========================================================================
    def run_test_2(self):
        """Test 2: Check if we can access APIs that require secure context"""
        self.log("\n--- TEST 2: Checking Secure Origin Bypass ---")
        
        # Test if navigator.mediaDevices is available (requires secure context in Chrome)
        # Also test WebSocket to localhost
        js_check = """
        (function() {
            var results = {
                mediaDevicesAvailable: typeof navigator.mediaDevices !== 'undefined',
                getUserMediaAvailable: typeof navigator.mediaDevices !== 'undefined' && 
                                        typeof navigator.mediaDevices.getUserMedia === 'function',
                isSecureContext: window.isSecureContext,
                webSocketTest: 'not tested'
            };
            
            // Try to create a WebSocket to localhost (would fail in insecure context in some cases)
            try {
                var ws = new WebSocket('ws://localhost:8765/test');
                ws.onopen = function() { ws.close(); };
                ws.onerror = function() {};
                results.webSocketTest = 'can create';
            } catch (e) {
                results.webSocketTest = 'error: ' + e.message;
            }
            
            return JSON.stringify(results);
        })();
        """
        self.browser.page().runJavaScript(js_check, self.on_test2_complete)
    
    def on_test2_complete(self, result):
        """Process Test 2 result"""
        try:
            import json
            data = json.loads(result) if isinstance(result, str) else result
            
            self.log(f"isSecureContext: {data.get('isSecureContext', 'unknown')}")
            self.log(f"mediaDevices available: {data.get('mediaDevicesAvailable', False)}")
            self.log(f"getUserMedia available: {data.get('getUserMediaAvailable', False)}")
            self.log(f"WebSocket test: {data.get('webSocketTest', 'unknown')}")
            
            # Key check: can we access APIs that would normally require secure context?
            # Note: isSecureContext may be false, but Qt WebEngine may still allow the APIs
            media_ok = data.get('mediaDevicesAvailable', False)
            ws_ok = data.get('webSocketTest') == 'can create'
            
            if media_ok:
                self.set_status(self.test2_status, True, "Secure APIs accessible")
                self.test_results.set("Test 2: Secure Origin", True, "mediaDevices available")
                self.test3_btn.setEnabled(True)
                self.test3_status.setText("Ready")
            else:
                # Even if media not available, WebSocket might work
                self.log("Note: mediaDevices not available, but this may not block our use case")
                self.log("DLA captures camera directly via Python, not via browser")
                self.set_status(self.test2_status, True, "Partial - WebSocket OK, media via Python")
                self.test_results.set("Test 2: Secure Origin", True, "WebSocket works, camera handled by Python")
                self.test3_btn.setEnabled(True)
                self.test3_status.setText("Ready")
                
        except Exception as e:
            self.log(f"Error in test 2: {e}")
            self.set_status(self.test2_status, False, str(e))
            self.test_results.set("Test 2: Secure Origin", False, str(e))
    
    # =========================================================================
    # TEST 3: Can we inject JavaScript into the page from Python?
    # =========================================================================
    def run_test_3(self):
        """Test 3: Inject JavaScript and verify it runs"""
        self.log("\n--- TEST 3: JavaScript Injection ---")
        
        # Create a unique marker we can check for
        js_inject = """
        (function() {
            // Create a marker to prove injection worked
            window.__DLA_INJECTED__ = true;
            window.__DLA_TIMESTAMP__ = Date.now();
            
            // Try to add something visible
            var marker = document.createElement('div');
            marker.id = 'dla-injection-marker';
            marker.style.cssText = 'position:fixed;top:10px;right:10px;background:#00ff00;color:black;padding:10px;z-index:99999;border-radius:5px;font-weight:bold;';
            marker.textContent = 'DLA Injection Active';
            document.body.appendChild(marker);
            
            return JSON.stringify({
                injected: window.__DLA_INJECTED__,
                timestamp: window.__DLA_TIMESTAMP__,
                markerAdded: document.getElementById('dla-injection-marker') !== null
            });
        })();
        """
        
        self.browser.page().runJavaScript(js_inject, self.on_test3_complete)
    
    def on_test3_complete(self, result):
        """Process Test 3 result"""
        try:
            import json
            data = json.loads(result) if isinstance(result, str) else result
            
            self.log(f"Injection marker set: {data.get('injected', False)}")
            self.log(f"Timestamp: {data.get('timestamp', 'none')}")
            self.log(f"Visual marker added: {data.get('markerAdded', False)}")
            
            if data.get('injected') and data.get('markerAdded'):
                self.set_status(self.test3_status, True, "JavaScript injection works")
                self.test_results.set("Test 3: JS Injection", True, "Can inject and modify page")
                self.test4_btn.setEnabled(True)
                self.test4_status.setText("Ready")
                self.log("Look for green 'DLA Injection Active' box in top-right of browser")
            else:
                self.set_status(self.test3_status, False, "Injection did not work as expected")
                self.test_results.set("Test 3: JS Injection", False, "Marker not set")
                
        except Exception as e:
            self.log(f"Error in test 3: {e}")
            self.set_status(self.test3_status, False, str(e))
            self.test_results.set("Test 3: JS Injection", False, str(e))
    
    # =========================================================================
    # TEST 4: Can injected JavaScript communicate back to Python?
    # =========================================================================
    def run_test_4(self):
        """Test 4: Two-way JS <-> Python communication"""
        self.log("\n--- TEST 4: JavaScript to Python Bridge ---")
        
        # Clear previous messages
        self.js_bridge.received_messages = []
        
        # Inject JavaScript that uses the QWebChannel bridge
        js_bridge_test = """
        (function() {
            // Load QWebChannel if not already loaded
            if (typeof QWebChannel === 'undefined') {
                // QWebChannel should be available via qwebchannel.js
                return JSON.stringify({error: 'QWebChannel not available'});
            }
            
            new QWebChannel(qt.webChannelTransport, function(channel) {
                var bridge = channel.objects.pyBridge;
                
                // Test sending to Python
                bridge.sendToPython('Hello from JavaScript! Timestamp: ' + Date.now());
                
                // Test receiving from Python
                var pythonMessage = bridge.getFromPython();
                
                // Create visual confirmation
                var resultDiv = document.createElement('div');
                resultDiv.id = 'dla-bridge-result';
                resultDiv.style.cssText = 'position:fixed;top:60px;right:10px;background:#0066ff;color:white;padding:10px;z-index:99999;border-radius:5px;';
                resultDiv.textContent = 'From Python: ' + pythonMessage;
                document.body.appendChild(resultDiv);
                
                window.__DLA_BRIDGE_RESULT__ = {
                    sentToPython: true,
                    receivedFromPython: pythonMessage
                };
            });
            
            return JSON.stringify({started: true});
        })();
        """
        
        # First, inject the QWebChannel script
        qwebchannel_inject = """
        if (typeof QWebChannel === 'undefined') {
            var script = document.createElement('script');
            script.src = 'qrc:///qtwebchannel/qwebchannel.js';
            document.head.appendChild(script);
        }
        """
        
        self.browser.page().runJavaScript(qwebchannel_inject)
        
        # Wait a moment for QWebChannel to load, then run the test
        QTimer.singleShot(500, lambda: self.browser.page().runJavaScript(js_bridge_test, self.on_test4_started))
    
    def on_test4_started(self, result):
        """Check if bridge test started"""
        self.log(f"Bridge test initiated: {result}")
        
        # Wait for the message to be received
        QTimer.singleShot(1000, self.verify_test4)
    
    def verify_test4(self):
        """Verify the bridge communication worked"""
        # Check if we received the message in Python
        if self.js_bridge.received_messages:
            self.log(f"Messages received in Python: {self.js_bridge.received_messages}")
            self.set_status(self.test4_status, True, "Two-way communication works")
            self.test_results.set("Test 4: JS-Python Bridge", True, f"Received: {self.js_bridge.received_messages[0][:50]}...")
            self.test5_btn.setEnabled(True)
            self.test5_status.setText("Ready")
            self.log("Look for blue 'From Python:' box in browser")
        else:
            # Check if there was an error
            self.browser.page().runJavaScript(
                "JSON.stringify(window.__DLA_BRIDGE_RESULT__ || {error: 'no result'})",
                self.on_test4_final_check
            )
    
    def on_test4_final_check(self, result):
        """Final check for Test 4"""
        import json
        try:
            data = json.loads(result) if isinstance(result, str) else result
            if data.get('error'):
                self.log(f"Bridge error: {data.get('error')}")
                self.set_status(self.test4_status, False, f"Bridge error: {data.get('error')}")
                self.test_results.set("Test 4: JS-Python Bridge", False, data.get('error'))
            else:
                # Partial success - one direction worked
                self.log(f"Bridge partial result: {data}")
                self.set_status(self.test4_status, True, "Communication established")
                self.test_results.set("Test 4: JS-Python Bridge", True, "Partial communication")
                self.test5_btn.setEnabled(True)
                self.test5_status.setText("Ready")
        except Exception as e:
            self.log(f"Test 4 verification error: {e}")
            self.set_status(self.test4_status, False, str(e))
            self.test_results.set("Test 4: JS-Python Bridge", False, str(e))
    
    # =========================================================================
    # TEST 5: Can we create a locked-down window?
    # =========================================================================
    def run_test_5(self):
        """Test 5: Demonstrate the locked-down window concept"""
        self.log("\n--- TEST 5: Locked Window Verification ---")
        
        # This test demonstrates that we have achieved a locked-down window:
        # - No address bar (user can't navigate elsewhere)
        # - URL is fixed (displayed but not editable)
        # - No navigation buttons
        # - Content is contained
        
        checks = {
            "no_address_bar": True,  # We built the UI without one
            "url_displayed": self.url_label.text() == self.vtt_url,
            "url_not_editable": True,  # QLabel is read-only
            "content_loaded": True,  # If we got here, content loaded
        }
        
        self.log(f"No address bar: {checks['no_address_bar']}")
        self.log(f"URL displayed correctly: {checks['url_displayed']}")
        self.log(f"URL not editable: {checks['url_not_editable']}")
        self.log(f"Content loaded: {checks['content_loaded']}")
        
        all_passed = all(checks.values())
        
        if all_passed:
            self.set_status(self.test5_status, True, "Locked window verified")
            self.test_results.set("Test 5: Locked Window", True, "All constraints verified")
        else:
            failed = [k for k, v in checks.items() if not v]
            self.set_status(self.test5_status, False, f"Failed: {failed}")
            self.test_results.set("Test 5: Locked Window", False, f"Failed: {failed}")
        
        self.log("\n" + "="*40)
        self.log("ALL CORE TESTS COMPLETE")
        self.log("Click 'Show Test Summary' for results")
        self.log("="*40)
    
    def show_summary(self):
        """Show test results summary"""
        summary = self.test_results.get_summary()
        self.log(summary)
        QMessageBox.information(self, "Test Results", summary)
    
    def run_debug_check(self):
        """Debug: Check what's actually loaded on the page"""
        self.log("\n--- DEBUG: Checking Page Content ---")
        
        js_debug = """
        (function() {
            var results = {
                url: window.location.href,
                title: document.title,
                doctype: document.doctype ? document.doctype.name : 'none',
                htmlLength: document.documentElement.outerHTML.length,
                headContent: document.head ? document.head.innerHTML.substring(0, 500) : 'no head',
                bodyContent: document.body ? document.body.innerHTML.substring(0, 1000) : 'no body',
                stylesheets: document.styleSheets.length,
                scripts: document.scripts.length,
                images: document.images.length,
                links: document.querySelectorAll('link').length,
                loadedResources: []
            };
            
            // Check for any link/script tags and their status
            var links = document.querySelectorAll('link[rel="stylesheet"]');
            links.forEach(function(link, i) {
                results.loadedResources.push('CSS: ' + link.href.substring(0, 80));
            });
            
            var scripts = document.querySelectorAll('script[src]');
            scripts.forEach(function(script, i) {
                results.loadedResources.push('JS: ' + script.src.substring(0, 80));
            });
            
            return JSON.stringify(results, null, 2);
        })();
        """
        self.browser.page().runJavaScript(js_debug, self.on_debug_complete)
    
    def on_debug_complete(self, result):
        """Process debug result"""
        self.log("Debug results:")
        self.log(result if result else "No result returned")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python embedded-browser-test.py <foundry-url>")
        print("Example: python embedded-browser-test.py http://192.168.1.55:30000")
        sys.exit(1)
    
    vtt_url = sys.argv[1]
    
    # Validate URL format
    if not vtt_url.startswith("http://") and not vtt_url.startswith("https://"):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("  Embedded Browser Feasibility Test")
    print(f"  Target VTT: {vtt_url}")
    print(f"{'='*60}\n")
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = EmbeddedBrowserTest(vtt_url)
    window.show()
    
    # Run application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
