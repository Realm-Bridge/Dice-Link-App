#!/usr/bin/env python3
"""
PyQt6 Test 2: Secure Origin Bypass
Tests whether WebSocket, WebRTC, and other restricted APIs work on HTTP in embedded browser.
First run: WITHOUT security bypass flags
Second run: WITH security bypass flags (if needed)
"""

import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# IMPORTANT: Set this BEFORE QApplication creation if you want to test WITH flags
USE_SECURITY_BYPASS = True  # Changed to True to test with bypass flags

# Get URL from command line for the unsafely-treat flag
TARGET_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:30000"

# Build the arguments to pass to QApplication
# These Chromium flags MUST be passed via sys.argv, NOT environment variable!
QT_ARGS = [sys.argv[0]]  # Start with program name

if USE_SECURITY_BYPASS:
    # Extract origin from URL for the unsafely-treat flag
    parsed = urlparse(TARGET_URL)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    
    # Add all Chromium flags to the argument list
    chromium_flags = [
        # THE KEY FLAG - tells Chromium to treat this specific HTTP origin as secure
        f'--unsafely-treat-insecure-origin-as-secure={origin}',
        # Additional flags for good measure
        '--disable-web-security',
        '--disable-features=CrossOriginOpenerPolicy',
        '--disable-features=CrossOriginEmbedderPolicy', 
        '--allow-running-insecure-content',
        '--disable-site-isolation-trials',
        '--disable-features=IsolateOrigins',
        '--disable-features=site-per-process',
        # Force treat as secure context
        '--test-type',
        '--ignore-certificate-errors',
    ]
    
    QT_ARGS.extend(chromium_flags)
    print(f"[BYPASS] Setting origin as secure: {origin}")
    print(f"[BYPASS] Passing {len(chromium_flags)} Chromium flags via sys.argv")

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtCore import QUrl, QTimer

SCRIPT_DIR = Path(__file__).resolve().parent

class SecureOriginPage(QWebEnginePage):
    """Custom page for capturing console messages"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.console_messages = []
    
    def javaScriptConsoleMessage(self, level, message, line, source):
        """Capture JavaScript console messages"""
        level_names = {0: "INFO", 1: "WARNING", 2: "ERROR"}
        level_name = level_names.get(level, "UNKNOWN")
        log_entry = f"[JS {level_name}] {message}"
        print(log_entry)
        self.console_messages.append(log_entry)

class SecureOriginTest(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.test_results = {}
        self.setup_ui()
        self.setup_browser()
        self.load_url()
    
    def setup_ui(self):
        """Setup UI"""
        self.setWindowTitle("PyQt6 Test 2: Secure Origin Bypass")
        self.setGeometry(100, 100, 1400, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Browser
        self.browser = QWebEngineView()
        main_layout.addWidget(self.browser, 3)
        
        # Control panel
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # Title
        title = QLabel("Secure Origin Tests")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        control_layout.addWidget(title)
        
        # Test buttons
        self.test_secure_context_btn = QPushButton("Test 1: Check Secure Context")
        self.test_secure_context_btn.clicked.connect(self.test_secure_context)
        control_layout.addWidget(self.test_secure_context_btn)
        
        self.test_websocket_btn = QPushButton("Test 2: WebSocket Connection")
        self.test_websocket_btn.clicked.connect(self.test_websocket)
        control_layout.addWidget(self.test_websocket_btn)
        
        self.test_media_devices_btn = QPushButton("Test 3: Media Devices API")
        self.test_media_devices_btn.clicked.connect(self.test_media_devices)
        control_layout.addWidget(self.test_media_devices_btn)
        
        self.test_all_btn = QPushButton("Run All Tests")
        self.test_all_btn.clicked.connect(self.run_all_tests)
        control_layout.addWidget(self.test_all_btn)
        
        # Output
        control_layout.addWidget(QLabel("Test Output:"))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        control_layout.addWidget(self.output)
        
        main_layout.addWidget(control_widget, 1)
    
    def setup_browser(self):
        """Setup browser settings"""
        page = SecureOriginPage()
        self.browser.setPage(page)
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        
        # Don't set AllowRunningInsecureContent here - we're testing if it's needed
        
        mode = "WITH security bypass" if USE_SECURITY_BYPASS else "WITHOUT security bypass"
        self.log(f"Browser initialized: {mode}")
        self.log(f"URL: {self.url}\n")
    
    def load_url(self):
        """Load the URL"""
        self.browser.setUrl(QUrl(self.url))
        QTimer.singleShot(2000, self.page_loaded)
    
    def page_loaded(self):
        """Called after page loads"""
        self.log("Page loaded. Ready to test secure origin restrictions.\n")
    
    def test_secure_context(self):
        """Test 1: Check if window.isSecureContext is true"""
        self.log("\n--- TEST 1: Secure Context ---")
        
        js = """
        (function() {
            return {
                isSecureContext: window.isSecureContext,
                protocol: window.location.protocol,
                hostname: window.location.hostname,
                port: window.location.port,
            };
        })();
        """
        self.browser.page().runJavaScript(js, self.handle_secure_context)
    
    def handle_secure_context(self, result):
        """Handle secure context result"""
        if result:
            self.log(f"Location: {result['protocol']}//{result['hostname']}:{result['port']}")
            if result['isSecureContext']:
                self.log("✓ window.isSecureContext = TRUE")
                self.log("✓ Page is treated as SECURE by browser")
                self.test_results['secure_context'] = True
            else:
                self.log("✗ window.isSecureContext = FALSE")
                self.log("✗ Page is treated as INSECURE (HTTP)")
                self.test_results['secure_context'] = False
    
    def test_websocket(self):
        """Test 2: Try WebSocket connection"""
        self.log("\n--- TEST 2: WebSocket Connection ---")
        
        js = """
        (function() {
            try {
                // Try to create WebSocket
                var ws = new WebSocket('ws://localhost:8080');
                ws.onopen = function() {
                    console.log('[WEBSOCKET] Connected successfully');
                };
                ws.onerror = function(e) {
                    console.log('[WEBSOCKET] Error: ' + e);
                };
                ws.onclose = function() {
                    console.log('[WEBSOCKET] Closed');
                };
                return 'WebSocket creation attempted';
            } catch(e) {
                return 'WebSocket error: ' + e.message;
            }
        })();
        """
        self.browser.page().runJavaScript(js, self.handle_websocket)
    
    def handle_websocket(self, result):
        """Handle WebSocket result"""
        self.log(f"WebSocket test: {result}")
        self.log("Check console above for WebSocket errors")
    
    def test_media_devices(self):
        """Test 3: Check mediaDevices API availability"""
        self.log("\n--- TEST 3: Media Devices API ---")
        
        js = """
        (function() {
            var results = {
                hasMediaDevices: !!navigator.mediaDevices,
                hasGetUserMedia: !!navigator.mediaDevices?.getUserMedia,
                hasEnumerateDevices: !!navigator.mediaDevices?.enumerateDevices,
            };
            
            if (navigator.mediaDevices) {
                try {
                    navigator.mediaDevices.enumerateDevices().then(function(devices) {
                        console.log('[MEDIA] Devices enumerated: ' + devices.length);
                    }).catch(function(err) {
                        console.log('[MEDIA] Error: ' + err.message);
                    });
                } catch(e) {
                    console.log('[MEDIA] Exception: ' + e.message);
                }
            }
            
            return results;
        })();
        """
        self.browser.page().runJavaScript(js, self.handle_media_devices)
    
    def handle_media_devices(self, result):
        """Handle mediaDevices result"""
        if result:
            self.log(f"navigator.mediaDevices exists: {result['hasMediaDevices']}")
            self.log(f"getUserMedia available: {result['hasGetUserMedia']}")
            self.log(f"enumerateDevices available: {result['hasEnumerateDevices']}")
            
            if result['hasMediaDevices']:
                self.log("✓ Media Devices API is AVAILABLE")
                self.test_results['media_devices'] = True
            else:
                self.log("✗ Media Devices API is BLOCKED")
                self.test_results['media_devices'] = False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("\n=== RUNNING ALL TESTS ===\n")
        self.test_secure_context()
        QTimer.singleShot(1000, self.test_websocket)
        QTimer.singleShot(2000, self.test_media_devices)
        QTimer.singleShot(3000, self.show_summary)
    
    def show_summary(self):
        """Show test summary"""
        self.log("\n=== TEST SUMMARY ===")
        self.log(f"Secure Context: {'PASS' if self.test_results.get('secure_context') else 'FAIL'}")
        self.log(f"Media Devices: {'PASS' if self.test_results.get('media_devices') else 'FAIL'}")
        self.log(f"\nSecurity Bypass Used: {'YES' if USE_SECURITY_BYPASS else 'NO'}")
        
        if self.test_results.get('secure_context'):
            self.log("\n✓ Secure origin restrictions are BYPASSED")
            self.log("✓ Embedded browser treats HTTP as secure context")
            self.log("✓ WebSocket and WebRTC should work")
        else:
            self.log("\n✗ Secure origin restrictions are ACTIVE")
            self.log("✗ Try again with USE_SECURITY_BYPASS = True")
    
    def log(self, message):
        """Add message to log output"""
        self.output.append(message)
        print(message)

def main():
    if len(sys.argv) < 2:
        print("Usage: python pyqt6-test2-secure-origin.py <URL>")
        print("Example: python pyqt6-test2-secure-origin.py http://localhost:30000")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # CRITICAL: Pass Chromium flags via QApplication arguments
    # This is how Qt WebEngine receives Chromium command-line switches
    print(f"[DEBUG] Passing args to QApplication: {QT_ARGS}")
    app = QApplication(QT_ARGS)
    test = SecureOriginTest(url)
    test.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
