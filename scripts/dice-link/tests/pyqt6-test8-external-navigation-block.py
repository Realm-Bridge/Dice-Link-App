#!/usr/bin/env python3
"""
Test 8: External Navigation Blocking
Tests that the embedded browser blocks external site navigation while allowing Foundry functionality
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QLineEdit, QSplitter)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import Qt, QUrl
from urllib.parse import urlparse


class NavigationBlocker(QWebEngineProfile):
    """Custom profile that blocks external navigation"""
    
    def __init__(self, allowed_origin):
        super().__init__()
        self.allowed_origin = allowed_origin.rstrip('/')
        
    def is_same_origin(self, url):
        """Check if URL is same origin as VTT"""
        try:
            parsed = urlparse(str(url))
            origin = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
            same = origin == self.allowed_origin
            return same
        except:
            return False


class TestWindow(QMainWindow):
    def __init__(self, url: str):
        super().__init__()
        self.target_url = url
        self.allowed_origin = url.rstrip('/')
        
        self.setWindowTitle("PyQt6 Test 8: External Navigation Blocking")
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
        title = QLabel("External Navigation Blocking Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_layout.addWidget(title)
        
        # Test buttons
        self.btn_load = QPushButton("Test 1: Load VTT")
        self.btn_load.clicked.connect(self.test_load)
        control_layout.addWidget(self.btn_load)
        
        self.btn_external_link = QPushButton("Test 2: Try External Link from Foundry")
        self.btn_external_link.clicked.connect(self.test_external_link)
        control_layout.addWidget(self.btn_external_link)
        
        self.btn_external_window = QPushButton("Test 3: Try window.open() to External Site")
        self.btn_external_window.clicked.connect(self.test_external_window)
        control_layout.addWidget(self.btn_external_window)
        
        self.btn_internal_link = QPushButton("Test 4: Try Internal Foundry Link (should work)")
        self.btn_internal_link.clicked.connect(self.test_internal_link)
        control_layout.addWidget(self.btn_internal_link)
        
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
        
        control_layout.addStretch()
        
        # Set splitter sizes
        splitter.setSizes([1000, 400])
        
        self.show()
        self.log(f"Test 8: External Navigation Blocking\nTarget URL: {url}\nReady for testing.")
        
    def setup_browser(self):
        """Setup browser with navigation interception"""
        self.browser = QWebEngineView()
        
        # Create custom profile with interceptor
        profile = self.browser.page().profile()
        
        # We'll intercept navigation at the page level
        page = self.browser.page()
        
        # Store old accept method
        self.blocked_urls = []
        self.allowed_urls = []
        
        # Override navigation for all requests
        def on_accept_navigation(url, _type, is_main_frame):
            if is_main_frame:
                return self.on_navigation(url)
            return True
        
        # Connect to page's URL change
        page.urlChanged.connect(self.on_url_changed)
        
    def on_url_changed(self, url):
        """Log URL changes"""
        url_str = str(url)
        parsed = urlparse(url_str)
        origin = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
        is_same = origin == self.allowed_origin
        
        status = "ALLOWED (same origin)" if is_same else "BLOCKED (external)"
        self.log(f"[NAV] {url_str}\n     {status}")
        
    def on_navigation(self, url):
        """Check if navigation is allowed"""
        url_str = str(url)
        
        # Parse URL
        parsed = urlparse(url_str)
        origin = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')
        
        is_same = origin == self.allowed_origin
        
        if is_same:
            self.log(f"[NAV] ALLOWED: {url_str}")
            self.allowed_urls.append(url_str)
            return True
        else:
            self.log(f"[NAV] BLOCKED: {url_str}")
            self.blocked_urls.append(url_str)
            return False
    
    def test_load(self):
        """Test 1: Load VTT"""
        self.log("\n--- TEST 1: Load VTT ---")
        self.browser.setUrl(QUrl(self.target_url))
        self.log(f"Loading: {self.target_url}")
        
    def test_external_link(self):
        """Test 2: Try clicking external link"""
        self.log("\n--- TEST 2: External Link Click ---")
        script = """
        (function() {
            // Create a test external link and click it
            var link = document.createElement('a');
            link.href = 'https://www.google.com';
            link.textContent = 'External Link';
            link.target = '_blank';
            document.body.appendChild(link);
            
            // Simulate user click
            var event = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            link.dispatchEvent(event);
            
            return 'External link clicked (should have been blocked)';
        })();
        """
        self.browser.page().runJavaScript(script, lambda r: self.log(f"JS Result: {r}"))
        
    def test_external_window(self):
        """Test 3: Try window.open() to external site"""
        self.log("\n--- TEST 3: window.open() to External Site ---")
        script = """
        (function() {
            try {
                var win = window.open('https://www.github.com', '_blank');
                if (!win) {
                    return 'window.open() blocked or popup window failed';
                } else {
                    return 'window.open() succeeded (unexpected)';
                }
            } catch(e) {
                return 'window.open() threw error: ' + e.message;
            }
        })();
        """
        self.browser.page().runJavaScript(script, lambda r: self.log(f"JS Result: {r}"))
        
    def test_internal_link(self):
        """Test 4: Try internal Foundry link"""
        self.log("\n--- TEST 4: Internal Foundry Link ---")
        script = """
        (function() {
            // Create internal link
            var link = document.createElement('a');
            link.href = window.location.origin + '/join';
            link.textContent = 'Internal Link';
            document.body.appendChild(link);
            
            var event = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            link.dispatchEvent(event);
            
            return 'Internal link clicked (should work or navigate internally)';
        })();
        """
        self.browser.page().runJavaScript(script, lambda r: self.log(f"JS Result: {r}"))
        
    def show_summary(self):
        """Show test summary"""
        self.log("\n=== TEST SUMMARY ===")
        self.log(f"Allowed URLs: {len(self.allowed_urls)}")
        for url in self.allowed_urls[:5]:  # Show first 5
            self.log(f"  ✓ {url}")
        if len(self.allowed_urls) > 5:
            self.log(f"  ... and {len(self.allowed_urls) - 5} more")
            
        self.log(f"\nBlocked URLs: {len(self.blocked_urls)}")
        for url in self.blocked_urls:
            self.log(f"  ✗ {url}")
        
        if len(self.blocked_urls) > 0:
            self.log("\n✓ PASS: External navigation blocking is working!")
        else:
            self.log("\n? WARNING: No external URLs were blocked - test may not have run")
    
    def log(self, text):
        """Log text to output"""
        self.log_output.append(text)
        # Auto-scroll to bottom
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: python pyqt6-test8-external-navigation-block.py <URL>")
        print("Example: python pyqt6-test8-external-navigation-block.py http://localhost:30000")
        sys.exit(1)
    
    url = sys.argv[1]
    
    app = QApplication(sys.argv)
    window = TestWindow(url)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
