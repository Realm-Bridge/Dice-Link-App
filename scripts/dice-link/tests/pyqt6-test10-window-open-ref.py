#!/usr/bin/env python3
"""
Test 10: Window.open() Reference Test
=======================================
Tests whether window.open() returns a valid window reference in Qt popups.
This is critical for the PopOut module to work.
"""

import sys
import json
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtCore import Qt, QUrl, QTimer
from urllib.parse import urlparse


class TestWindow(QMainWindow):
    def __init__(self, allowed_origin):
        super().__init__()
        self.allowed_origin = allowed_origin
        self.popup_windows = []
        
        self.setWindowTitle("window.open() Reference Test")
        self.resize(900, 700)
        
        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Browser
        self.setup_browser()
        layout.addWidget(self.browser)
        
        # Test buttons
        self.btn_test1 = QPushButton("Test 1: Load VTT")
        self.btn_test1.clicked.connect(self.test_load_vtt)
        layout.addWidget(self.btn_test1)
        
        self.btn_test2 = QPushButton("Test 2: Test window.open() Reference")
        self.btn_test2.clicked.connect(self.test_window_open_reference)
        layout.addWidget(self.btn_test2)
        
        self.btn_test3 = QPushButton("Test 3: Communicate with Popup")
        self.btn_test3.clicked.connect(self.test_communicate_with_popup)
        layout.addWidget(self.btn_test3)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        
    def log(self, message):
        """Log message to output"""
        self.log_output.append(message)
        print(message)
    
    def setup_browser(self):
        """Set up browser"""
        profile = QWebEngineProfile.defaultProfile()
        
        self.browser = QWebEngineView()
        self.custom_page = CustomWebPage(profile, self.allowed_origin, self.log, self)
        self.browser.setPage(self.custom_page)
        
        settings = self.custom_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
    
    def test_load_vtt(self):
        """Test 1: Load VTT"""
        self.log("\n--- TEST 1: Loading VTT ---")
        url = self.allowed_origin
        self.browser.setUrl(QUrl(url))
        self.log(f"Loading: {url}")
    
    def test_window_open_reference(self):
        """Test 2: Check if window.open() returns valid reference"""
        self.log("\n--- TEST 2: window.open() Reference Test ---")
        
        test_script = """
        (function() {
            // Test 1: Simple window.open()
            var popupURL = window.location.href + "?popout-test=true";
            var popupWindow = window.open(popupURL, "test_popup", "width=600,height=700");
            
            if (popupWindow === null) {
                return JSON.stringify({
                    result: "FAIL",
                    reason: "window.open() returned null - popups may be blocked"
                });
            }
            
            // Test 2: Check if we can access popup properties
            try {
                var testAccess = popupWindow.name;
                return JSON.stringify({
                    result: "SUCCESS",
                    windowRefValid: true,
                    windowName: testAccess,
                    canAccessProperties: true,
                    message: "window.open() returns valid reference - PopOut module can work!"
                });
            } catch(e) {
                return JSON.stringify({
                    result: "PARTIAL",
                    windowRefNotNull: true,
                    cannotAccessProperties: true,
                    error: e.message
                });
            }
        })();
        """
        
        def on_result(result):
            self.log(f"\nwindow.open() result: {result}")
            try:
                data = json.loads(result)
                if data.get("result") == "SUCCESS":
                    self.log("\n✓ SUCCESS: window.open() returns valid reference")
                    self.log("✓ The PopOut module SHOULD work with this setup")
                elif data.get("result") == "FAIL":
                    self.log(f"\n✗ FAIL: {data.get('reason')}")
                else:
                    self.log(f"\n? PARTIAL: {data}")
            except:
                self.log(f"Parse error: {result}")
        
        self.browser.page().runJavaScript(test_script, on_result)
    
    def test_communicate_with_popup(self):
        """Test 3: Test communication with popup window"""
        self.log("\n--- TEST 3: Popup Communication Test ---")
        
        comm_script = """
        (function() {
            // Store reference to popup created in Test 2
            if (typeof window.lastPopup === 'undefined') {
                // Create new popup for this test
                var popupURL = window.location.href + "?popout-test=true";
                window.lastPopup = window.open(popupURL, "comm_test", "width=600,height=700");
            }
            
            if (!window.lastPopup) {
                return JSON.stringify({
                    error: "No popup window available"
                });
            }
            
            // Test: Try to set a variable in the popup
            try {
                window.lastPopup.testValue = "Hello from parent";
                var readBack = window.lastPopup.testValue;
                
                return JSON.stringify({
                    canWrite: true,
                    canRead: true,
                    value: readBack,
                    message: "Two-way communication works!"
                });
            } catch(e) {
                return JSON.stringify({
                    error: e.message,
                    message: "Cannot communicate with popup"
                });
            }
        })();
        """
        
        def on_result(result):
            self.log(f"\nCommunication result: {result}")
            try:
                data = json.loads(result)
                if data.get("canWrite") and data.get("canRead"):
                    self.log("✓ SUCCESS: Can communicate with popup window")
                    self.log(f"✓ Value: {data.get('value')}")
                    self.log("✓ The PopOut module's window reference mechanism will work")
                else:
                    self.log(f"✗ Cannot communicate: {data.get('error')}")
            except:
                self.log(f"Parse error: {result}")
        
        self.browser.page().runJavaScript(comm_script, on_result)


class CustomWebPage(QWebEnginePage):
    """Custom page that allows and tracks popup windows"""
    
    def __init__(self, profile, allowed_origin, log_callback, main_window=None, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin
        self.log = log_callback
        self.main_window = main_window
        self.popup_pages = []
        
        self.newWindowRequested.connect(self.handle_new_window)
    
    def is_same_origin(self, url_str: str) -> bool:
        if not url_str or url_str == 'about:blank':
            return True
        parsed_new = urlparse(url_str)
        parsed_allowed = urlparse(self.allowed_origin)
        return (parsed_new.scheme == parsed_allowed.scheme and 
                parsed_new.netloc == parsed_allowed.netloc)
    
    def handle_new_window(self, request):
        """Handle window.open() requests"""
        requested_url = request.requestedUrl().toString()
        self.log(f"\n[WINDOW.OPEN] URL: {requested_url}")
        
        if self.is_same_origin(requested_url):
            self.log("[WINDOW.OPEN] ALLOWED: Creating popup")
            
            # Create popup page
            popup_page = PopupWebPage(self.profile(), self.allowed_origin, self.log)
            
            # CRITICAL: Use openIn() to get the window reference back
            request.openIn(popup_page)
            
            self.log("[WINDOW.OPEN] Popup window created via openIn()")
            self.popup_pages.append(popup_page)
        else:
            self.log("[WINDOW.OPEN] BLOCKED: External origin")
            request.reject()
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        url_str = url.toString()
        if self.is_same_origin(url_str) or url_str.startswith('javascript:'):
            return True
        return False


class PopupWebPage(QWebEnginePage):
    """Page for popup windows"""
    
    def __init__(self, profile, allowed_origin, log_callback, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin
        self.log = log_callback
    
    def is_same_origin(self, url_str: str) -> bool:
        if not url_str or url_str == 'about:blank':
            return True
        parsed_new = urlparse(url_str)
        parsed_allowed = urlparse(self.allowed_origin)
        return (parsed_new.scheme == parsed_allowed.scheme and 
                parsed_new.netloc == parsed_allowed.netloc)
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        url_str = url.toString()
        if self.is_same_origin(url_str) or url_str.startswith('javascript:'):
            return True
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python pyqt6-test10-window-open-ref.py <VTT_URL>")
        print("Example: python pyqt6-test10-window-open-ref.py http://localhost:30000")
        sys.exit(1)
    
    vtt_url = sys.argv[1]
    
    app = QApplication(sys.argv)
    window = TestWindow(vtt_url)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
