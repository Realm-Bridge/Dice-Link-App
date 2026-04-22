"""
PyQt6 Test 3/4: QWebChannel Bridge Test
Tests JavaScript injection and Python-to-JavaScript communication
using Qt's INTERNAL transport mechanism (NOT WebSocket)

This bypasses the secure context requirement because QWebChannel
uses Qt's internal IPC, not browser WebSocket API.
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl


class PythonBridge(QObject):
    """
    Python object that will be exposed to JavaScript.
    JavaScript can call methods on this object and receive signals from it.
    """
    
    # Signal that can be emitted to JavaScript
    messageFromPython = pyqtSignal(str)
    
    def __init__(self, log_callback, parent=None):
        super().__init__(parent)
        self.log = log_callback
        self.message_count = 0
    
    @pyqtSlot(str)
    def receiveFromJS(self, message):
        """Called by JavaScript to send data to Python"""
        self.message_count += 1
        self.log(f"[PYTHON RECEIVED #{self.message_count}] {message}")
        self.log("SUCCESS: JavaScript -> Python communication works!")
        
    @pyqtSlot(str, result=str)
    def echo(self, message):
        """Called by JavaScript, returns a value back"""
        self.log(f"[PYTHON ECHO] Received: {message}")
        return f"Python echoed: {message}"
    
    @pyqtSlot(result=str)
    def getPythonInfo(self):
        """JavaScript can call this to get info from Python"""
        import platform
        info = f"Python {platform.python_version()} on {platform.system()}"
        self.log(f"[PYTHON INFO] Sending: {info}")
        return info
    
    def sendToPython(self, message):
        """Python can call this to send message to JavaScript"""
        self.log(f"[PYTHON SENDING] {message}")
        self.messageFromPython.emit(message)


class WebChannelTestWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.setWindowTitle("PyQt6 Test 3/4: QWebChannel Bridge")
        self.setGeometry(100, 100, 1400, 900)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Browser on left
        self.browser = QWebEngineView()
        self.setup_browser()
        layout.addWidget(self.browser, 7)
        
        # Control panel on right
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        layout.addWidget(control_panel, 3)
        
        # Title
        title = QLabel("QWebChannel Bridge Tests")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        control_layout.addWidget(title)
        
        # Test buttons
        self.btn_inject = QPushButton("Test 1: Inject QWebChannel JS")
        self.btn_inject.clicked.connect(self.test_inject_webchannel)
        control_layout.addWidget(self.btn_inject)
        
        self.btn_py_to_js = QPushButton("Test 2: Python -> JavaScript")
        self.btn_py_to_js.clicked.connect(self.test_python_to_js)
        control_layout.addWidget(self.btn_py_to_js)
        
        self.btn_js_to_py = QPushButton("Test 3: JavaScript -> Python")
        self.btn_js_to_py.clicked.connect(self.test_js_to_python)
        control_layout.addWidget(self.btn_js_to_py)
        
        self.btn_echo = QPushButton("Test 4: Round-trip Echo")
        self.btn_echo.clicked.connect(self.test_echo)
        control_layout.addWidget(self.btn_echo)
        
        self.btn_all = QPushButton("Run All Tests")
        self.btn_all.clicked.connect(self.run_all_tests)
        self.btn_all.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.btn_all)
        
        # Message input
        control_layout.addWidget(QLabel("Send message to JS:"))
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type message here...")
        self.msg_input.returnPressed.connect(self.send_custom_message)
        control_layout.addWidget(self.msg_input)
        
        btn_send = QPushButton("Send to JavaScript")
        btn_send.clicked.connect(self.send_custom_message)
        control_layout.addWidget(btn_send)
        
        # Log output
        control_layout.addWidget(QLabel("Test Output:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        control_layout.addWidget(self.log_output)
        
        # Setup QWebChannel with Python bridge
        self.setup_webchannel()
        
        # Load page
        self.browser.setUrl(QUrl(url))
        self.browser.loadFinished.connect(self.on_page_loaded)
        
        self.log(f"QWebChannel Bridge Test Started")
        self.log(f"URL: {url}")
        self.log("Waiting for page to load...")
    
    def log(self, message):
        self.log_output.append(message)
        print(message)
    
    def setup_browser(self):
        """Configure browser settings"""
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
    
    def setup_webchannel(self):
        """Setup QWebChannel with Python bridge object"""
        # Create the channel
        self.channel = QWebChannel()
        
        # Create the Python bridge object
        self.bridge = PythonBridge(self.log)
        
        # Register the bridge object - it will be accessible as 'pythonBridge' in JS
        self.channel.registerObject("pythonBridge", self.bridge)
        
        # Attach channel to the page
        self.browser.page().setWebChannel(self.channel)
        
        self.log("QWebChannel created and attached to page")
        self.log("Python bridge registered as 'pythonBridge'")
    
    def on_page_loaded(self, ok):
        if ok:
            self.log("\nPage loaded successfully!")
            self.log("Ready to test QWebChannel bridge.")
            self.log("\nNOTE: This uses Qt's INTERNAL transport,")
            self.log("NOT WebSocket - so secure context doesn't matter!")
        else:
            self.log("ERROR: Page failed to load")
    
    def test_inject_webchannel(self):
        """Test 1: Inject qwebchannel.js and initialize the channel"""
        self.log("\n--- TEST 1: Inject QWebChannel JS ---")
        
        # The qwebchannel.js script that enables JS to talk to Python
        # When running in Qt WebEngine, qt.webChannelTransport is available
        inject_script = """
        (function() {
            // Check if qt.webChannelTransport exists (Qt's internal transport)
            if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                console.error('qt.webChannelTransport not available!');
                return JSON.stringify({
                    success: false,
                    error: 'qt.webChannelTransport not available',
                    hasQt: typeof qt !== 'undefined'
                });
            }
            
            // Load QWebChannel using Qt's internal transport (NOT WebSocket!)
            new QWebChannel(qt.webChannelTransport, function(channel) {
                // Make the Python bridge globally accessible
                window.pythonBridge = channel.objects.pythonBridge;
                
                // Signal that we're ready
                window.webChannelReady = true;
                
                console.log('QWebChannel initialized successfully!');
                console.log('pythonBridge available:', typeof window.pythonBridge);
                
                // Connect to signals from Python
                if (window.pythonBridge && window.pythonBridge.messageFromPython) {
                    window.pythonBridge.messageFromPython.connect(function(message) {
                        console.log('Received from Python:', message);
                        // You could update UI here
                    });
                }
            });
            
            return JSON.stringify({
                success: true,
                hasQt: true,
                hasTransport: true
            });
        })();
        """
        
        # First, we need to inject the qwebchannel.js library
        # In Qt WebEngine, it's available at qrc:///qtwebchannel/qwebchannel.js
        load_qwebchannel_js = """
        (function() {
            return new Promise(function(resolve, reject) {
                var script = document.createElement('script');
                script.src = 'qrc:///qtwebchannel/qwebchannel.js';
                script.onload = function() {
                    resolve('QWebChannel.js loaded');
                };
                script.onerror = function() {
                    reject('Failed to load qwebchannel.js');
                };
                document.head.appendChild(script);
            });
        })();
        """
        
        def on_qwebchannel_loaded(result):
            self.log(f"QWebChannel.js load result: {result}")
            # Now initialize the channel
            self.browser.page().runJavaScript(inject_script, self.on_channel_initialized)
        
        self.browser.page().runJavaScript(load_qwebchannel_js, on_qwebchannel_loaded)
    
    def on_channel_initialized(self, result):
        self.log(f"Channel initialization result: {result}")
        if result and 'success' in str(result):
            self.log("SUCCESS: QWebChannel initialized!")
            self.log("JavaScript can now talk to Python via qt.webChannelTransport")
        else:
            self.log("WARNING: Channel may not be fully initialized yet")
    
    def test_python_to_js(self):
        """Test 2: Send message from Python to JavaScript"""
        self.log("\n--- TEST 2: Python -> JavaScript ---")
        
        # Emit signal to JavaScript
        self.bridge.messageFromPython.emit("Hello from Python!")
        self.log("Signal emitted. Check browser console for received message.")
        
        # Also try direct JavaScript execution to verify
        check_script = """
        (function() {
            if (window.pythonBridge) {
                return 'pythonBridge is available in JavaScript';
            } else {
                return 'pythonBridge NOT available yet - run Test 1 first';
            }
        })();
        """
        self.browser.page().runJavaScript(check_script, lambda r: self.log(f"JS check: {r}"))
    
    def test_js_to_python(self):
        """Test 3: Have JavaScript call Python"""
        self.log("\n--- TEST 3: JavaScript -> Python ---")
        
        js_call_python = """
        (function() {
            if (!window.pythonBridge) {
                return 'ERROR: pythonBridge not available - run Test 1 first';
            }
            
            // Call Python's receiveFromJS method
            window.pythonBridge.receiveFromJS('Hello from JavaScript!');
            return 'Called pythonBridge.receiveFromJS()';
        })();
        """
        self.browser.page().runJavaScript(js_call_python, lambda r: self.log(f"JS result: {r}"))
    
    def test_echo(self):
        """Test 4: Round-trip - JS calls Python, gets response"""
        self.log("\n--- TEST 4: Round-trip Echo ---")
        
        js_echo = """
        (function() {
            if (!window.pythonBridge) {
                return 'ERROR: pythonBridge not available - run Test 1 first';
            }
            
            // Call Python's echo method and get response
            window.pythonBridge.echo('Test message from JS', function(response) {
                console.log('Echo response:', response);
                // Store for retrieval
                window.lastEchoResponse = response;
            });
            
            return 'Echo request sent - check Python output';
        })();
        """
        
        def check_response(result):
            self.log(f"JS result: {result}")
            # Give time for async response
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self.check_echo_response)
        
        self.browser.page().runJavaScript(js_echo, check_response)
    
    def check_echo_response(self):
        check_script = "window.lastEchoResponse || 'No response yet';"
        self.browser.page().runJavaScript(check_script, lambda r: self.log(f"Echo response in JS: {r}"))
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("\n=== RUNNING ALL TESTS ===")
        self.test_inject_webchannel()
        
        # Delay subsequent tests to allow channel to initialize
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self.test_python_to_js)
        QTimer.singleShot(2000, self.test_js_to_python)
        QTimer.singleShot(3000, self.test_echo)
        QTimer.singleShot(4000, self.print_summary)
    
    def print_summary(self):
        self.log("\n=== TEST SUMMARY ===")
        self.log(f"Messages received from JS: {self.bridge.message_count}")
        if self.bridge.message_count > 0:
            self.log("\nSUCCESS: QWebChannel bridge is WORKING!")
            self.log("This proves Python <-> JavaScript communication")
            self.log("works WITHOUT WebSocket and WITHOUT secure context!")
        else:
            self.log("\nWARNING: No messages received from JavaScript yet")
            self.log("The channel may still be initializing.")
    
    def send_custom_message(self):
        """Send custom message from input field to JavaScript"""
        message = self.msg_input.text()
        if message:
            self.log(f"\n[CUSTOM MESSAGE] Sending to JS: {message}")
            self.bridge.messageFromPython.emit(message)
            self.msg_input.clear()


def main():
    if len(sys.argv) < 2:
        print("Usage: python pyqt6-test3-webchannel-bridge.py <URL>")
        print("Example: python pyqt6-test3-webchannel-bridge.py http://localhost:30000")
        sys.exit(1)
    
    url = sys.argv[1]
    
    app = QApplication(sys.argv)
    window = WebChannelTestWindow(url)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
