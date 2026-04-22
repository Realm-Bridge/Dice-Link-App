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
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
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


class PopupWindow(QMainWindow):
    """Window container for Foundry pop-outs"""
    
    def __init__(self, web_view, log_callback):
        super().__init__()
        self.log = log_callback
        self.web_view = web_view
        
        self.setWindowTitle("Foundry Pop-out")
        self.resize(600, 700)
        
        self.setCentralWidget(web_view)
        
        # Update title when page title changes
        web_view.page().titleChanged.connect(self.on_title_changed)
        
        self.log("[POPUP] Window created")
    
    def on_title_changed(self, title):
        if title and title != "about:blank":
            self.setWindowTitle(title)


class FoundryWebView(QWebEngineView):
    """
    Custom WebEngineView that properly handles window.open() by overriding createWindow().
    
    This is the KEY fix: when JavaScript calls window.open(), Qt calls createWindow()
    and the RETURNED view becomes the popup. JavaScript gets a reference to this window,
    which is what Foundry's PopOut module needs.
    """
    
    def __init__(self, allowed_origin, log_callback, parent=None):
        super().__init__(parent)
        self.allowed_origin = allowed_origin
        self.log = log_callback
        self.popup_windows = []  # Keep references to prevent garbage collection
        
        # Set custom page for navigation blocking
        self.custom_page = FoundryWebPage(self.page().profile(), allowed_origin, log_callback)
        self.setPage(self.custom_page)
    
    def createWindow(self, window_type):
        """
        Override createWindow - called when JavaScript uses window.open().
        
        The returned QWebEngineView's page becomes the popup window that
        JavaScript can interact with. This gives Foundry's PopOut module
        the window reference it needs to write to popout.document, etc.
        """
        self.log(f"\n--- createWindow() called ---")
        self.log(f"Window type: {window_type}")
        
        # Create a new view for the popup (this will be returned to JavaScript)
        popup_view = FoundryPopupView(self.allowed_origin, self.log)
        
        # Create window container and show it
        popup_window = PopupWindow(popup_view, self.log)
        popup_window.show()
        
        # Keep reference to prevent garbage collection
        self.popup_windows.append(popup_window)
        
        self.log("Popup view created and returned to JavaScript")
        
        # Return the view - JavaScript's window.open() gets this as the popup window
        return popup_view


class FoundryPopupView(QWebEngineView):
    """WebEngineView for popup windows - can create nested popups if needed"""
    
    def __init__(self, allowed_origin, log_callback, parent=None):
        super().__init__(parent)
        self.allowed_origin = allowed_origin
        self.log = log_callback
        self.popup_windows = []
        
        # Set custom page with navigation restrictions
        self.custom_page = FoundryWebPage(self.page().profile(), allowed_origin, log_callback)
        self.setPage(self.custom_page)
    
    def createWindow(self, window_type):
        """Allow nested popups with same restrictions"""
        self.log(f"[POPUP] Nested createWindow() called")
        
        popup_view = FoundryPopupView(self.allowed_origin, self.log)
        popup_window = PopupWindow(popup_view, self.log)
        popup_window.show()
        self.popup_windows.append(popup_window)
        
        return popup_view


class FoundryWebPage(QWebEnginePage):
    """Custom web page - only blocks external navigation"""
    
    def __init__(self, profile, allowed_origin, log_callback, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin
        self.log = log_callback
        
    def is_same_origin(self, url_str: str) -> bool:
        """Check if URL is same origin as allowed Foundry server"""
        if not url_str or url_str == 'about:blank':
            return True
        
        parsed_new = urlparse(url_str)
        parsed_allowed = urlparse(self.allowed_origin)
        
        return (parsed_new.scheme == parsed_allowed.scheme and 
                parsed_new.netloc == parsed_allowed.netloc)
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Only block external navigation"""
        url_str = url.toString()
        
        if self.is_same_origin(url_str):
            return True
        
        if url_str.startswith('javascript:'):
            return True
        
        self.log(f"\nBLOCKED: External navigation to {url_str}")
        return False


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
        
        self.btn_window_ref = QPushButton("Test 3b: Check window.open() Reference")
        self.btn_window_ref.clicked.connect(self.test_window_reference)
        control_layout.addWidget(self.btn_window_ref)
        
        self.btn_popout_ops = QPushButton("Test 3c: Test PopOut Operations")
        self.btn_popout_ops.clicked.connect(self.test_popout_operations)
        control_layout.addWidget(self.btn_popout_ops)
        
        self.btn_write_persist = QPushButton("Test 3d: Check Write Persistence")
        self.btn_write_persist.clicked.connect(self.test_popout_write_persistence)
        control_layout.addWidget(self.btn_write_persist)
        
        self.btn_debug_popout = QPushButton("Test 3e: Debug PopOut Module (install hooks)")
        self.btn_debug_popout.clicked.connect(self.test_debug_popout_module)
        control_layout.addWidget(self.btn_debug_popout)
        
        self.btn_check_calls = QPushButton("Test 3e-ii: Check Captured Calls (after pop-out)")
        self.btn_check_calls.clicked.connect(self.test_check_popout_calls)
        control_layout.addWidget(self.btn_check_calls)
        
        self.btn_popout_workflow = QPushButton("Test 3f: Full Pop-out Workflow Test")
        self.btn_popout_workflow.clicked.connect(self.test_popout_workflow)
        control_layout.addWidget(self.btn_popout_workflow)
        
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
        """Set up browser with custom view that properly handles window.open()"""
        # Use custom FoundryWebView that overrides createWindow()
        # This is the KEY to making Foundry's PopOut module work
        self.browser = FoundryWebView(self.allowed_origin, self.log)
        
        # Configure settings
        settings = self.browser.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        
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
    
    def test_window_reference(self):
        """Test 3b: Check if window.open() returns a valid window reference"""
        self.log("\n--- TEST 3b: window.open() Reference Test ---")
        self.log("This test checks if window.open() returns a valid window object")
        self.log("(Required for Foundry's PopOut module to work)")
        
        ref_test_script = """
        (function() {
            try {
                // Try to open a blank window
                var popupWin = window.open('about:blank', 'test_popup_' + Date.now());
                
                if (popupWin === null) {
                    return JSON.stringify({
                        success: false,
                        reference: 'null',
                        message: 'window.open() returned null - popup blocked or not supported'
                    });
                }
                
                // Check if we can access window properties
                try {
                    var canAccess = typeof popupWin.document !== 'undefined';
                    popupWin.close();
                    
                    return JSON.stringify({
                        success: true,
                        reference: 'valid',
                        canAccess: canAccess,
                        message: 'window.open() returns valid reference - PopOut module should work!'
                    });
                } catch(e) {
                    return JSON.stringify({
                        success: false,
                        reference: 'object but restricted',
                        message: 'Got reference but cannot access properties: ' + e.message
                    });
                }
            } catch(e) {
                return JSON.stringify({
                    success: false,
                    error: e.message,
                    message: 'Exception thrown: ' + e.message
                });
            }
        })();
        """
        
        def on_result(result):
            try:
                import json
                data = json.loads(result)
                
                self.log(f"\nwindow.open() Reference Test Results:")
                self.log(f"  Success: {data.get('success', False)}")
                self.log(f"  Reference: {data.get('reference', 'unknown')}")
                self.log(f"  Message: {data.get('message', 'N/A')}")
                
                if data.get('success'):
                    self.log(f"\nPASS: window.open() returns valid reference")
                    self.log(f"Foundry's PopOut module SHOULD work with this implementation")
                    self.test_results['window_ref'] = True
                else:
                    self.log(f"\nFAIL: window.open() does not return valid reference")
                    self.log(f"PopOut module will NOT work as-is")
                    self.test_results['window_ref'] = False
            except Exception as e:
                self.log(f"Error parsing result: {e}")
                self.log(f"Raw result: {result}")
        
        self.browser.page().runJavaScript(ref_test_script, on_result)
        
    def test_popout_operations(self):
        """Test 3c: Test if PopOut module's critical operations work"""
        self.log("\n--- TEST 3c: PopOut Module Operations ---")
        self.log("This tests the EXACT operations Foundry's PopOut module needs:")
        self.log("1. window.open() returns a reference")
        self.log("2. popout.document.open() works")
        self.log("3. popout.document.write() works")
        self.log("4. adoptNode() can move DOM between windows")
        
        ops_test_script = """
        (function() {
            var results = {
                windowOpenWorks: false,
                documentOpenWorks: false,
                documentWriteWorks: false,
                adoptNodeWorks: false,
                errors: []
            };
            
            try {
                // Test 1: window.open() returns reference
                var popupWin = window.open('about:blank', 'popout_ops_test_' + Date.now());
                
                if (popupWin === null) {
                    results.errors.push('window.open() returned null');
                    return JSON.stringify(results);
                }
                
                results.windowOpenWorks = true;
                
                // Test 2 & 3: document.open() and document.write()
                try {
                    popupWin.document.open();
                    results.documentOpenWorks = true;
                    
                    // Try to write HTML
                    popupWin.document.write('<html><body>Test Content</body></html>');
                    results.documentWriteWorks = true;
                    
                    popupWin.document.close();
                } catch(e) {
                    results.errors.push('document operations failed: ' + e.message);
                }
                
                // Test 4: adoptNode() - move DOM from main to popup
                try {
                    var testElement = document.createElement('div');
                    testElement.textContent = 'Adopted Element';
                    
                    // This is what PopOut module does
                    var adoptedElement = popupWin.document.adoptNode(testElement);
                    if (adoptedElement !== null) {
                        results.adoptNodeWorks = true;
                        popupWin.document.body.appendChild(adoptedElement);
                    }
                } catch(e) {
                    results.errors.push('adoptNode failed: ' + e.message);
                }
                
                popupWin.close();
                
            } catch(e) {
                results.errors.push('Unexpected error: ' + e.message);
            }
            
            return JSON.stringify(results);
        })();
        """
        
        def on_result(result):
            try:
                import json
                data = json.loads(result)
                
                self.log(f"\nPopOut Module Operations Test Results:")
                self.log(f"  window.open() returns reference: {data.get('windowOpenWorks', False)}")
                self.log(f"  popout.document.open() works: {data.get('documentOpenWorks', False)}")
                self.log(f"  popout.document.write() works: {data.get('documentWriteWorks', False)}")
                self.log(f"  adoptNode() works: {data.get('adoptNodeWorks', False)}")
                
                errors = data.get('errors', [])
                if errors:
                    self.log(f"\nErrors encountered:")
                    for error in errors:
                        self.log(f"  - {error}")
                
                # Check if all critical operations work
                all_work = (data.get('windowOpenWorks') and 
                           data.get('documentOpenWorks') and 
                           data.get('documentWriteWorks') and
                           data.get('adoptNodeWorks'))
                
                if all_work:
                    self.log(f"\nPASS: All PopOut module operations work!")
                    self.log(f"Foundry's PopOut module SHOULD work correctly")
                    self.test_results['popout_ops'] = True
                else:
                    self.log(f"\nFAIL: Some PopOut operations don't work")
                    self.log(f"This explains why pop-outs fail in the embedded browser")
                    self.test_results['popout_ops'] = False
                    
            except Exception as e:
                self.log(f"Error parsing result: {e}")
                self.log(f"Raw result: {result}")
        
        self.browser.page().runJavaScript(ops_test_script, on_result)
        
    def test_popout_write_persistence(self):
        """Test 3d: Check if document.write() content persists in popup"""
        self.log("\n--- TEST 3d: Document.write() Persistence ---")
        self.log("This tests if document.write() actually writes to the popup document")
        
        persistence_test = """
        (function() {
            var results = {
                writtenContent: null,
                contentReadBack: null,
                writePersisted: false,
                error: null
            };
            
            try {
                // Open popup
                var popupWin = window.open('about:blank', 'persistence_test_' + Date.now());
                if (!popupWin) {
                    results.error = 'window.open() returned null';
                    return JSON.stringify(results);
                }
                
                // Write content
                var testContent = '<html><body><h1>Test Content</h1><p>Written via document.write()</p></body></html>';
                popupWin.document.open();
                popupWin.document.write(testContent);
                popupWin.document.close();
                
                results.writtenContent = testContent;
                
                // Try to read it back immediately
                try {
                    var readContent = popupWin.document.documentElement.outerHTML;
                    results.contentReadBack = readContent.substring(0, 100);  // First 100 chars
                    
                    // Check if our content is there
                    if (readContent.includes('Test Content')) {
                        results.writePersisted = true;
                    }
                } catch(e) {
                    results.error = 'Cannot read back content: ' + e.message;
                }
                
                popupWin.close();
                
            } catch(e) {
                results.error = 'Exception: ' + e.message;
            }
            
            return JSON.stringify(results);
        })();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                
                self.log(f"\nDocument.write() Persistence Test Results:")
                self.log(f"  Written content: {data.get('writtenContent')[:50] if data.get('writtenContent') else 'None'}...")
                self.log(f"  Content persisted: {data.get('writePersisted', False)}")
                self.log(f"  Read back: {data.get('contentReadBack', 'Failed to read')}")
                
                if data.get('error'):
                    self.log(f"  Error: {data['error']}")
                
                if data.get('writePersisted'):
                    self.log(f"\nPASS: document.write() content persists in popup")
                    self.test_results['write_persist'] = True
                else:
                    self.log(f"\nFAIL: document.write() content does NOT persist")
                    self.log(f"This explains why PopOut module cannot write to popup")
                    self.test_results['write_persist'] = False
                    
            except Exception as e:
                self.log(f"Error parsing result: {e}")
                self.log(f"Raw result: {result}")
        
        self.browser.page().runJavaScript(persistence_test, on_result)
        
    def test_debug_popout_module(self):
        """Test 3e: Debug the PopOut module to see what's happening"""
        self.log("\n--- TEST 3e: Debug PopOut Module ---")
        self.log("Injecting debug hooks into Foundry's PopOut module...")
        
        debug_script = """
        (function() {
            var debugInfo = {
                foundryReady: false,
                popoutModuleClassExists: false,
                popoutSingletonExists: false,
                popoutModuleInGame: false,
                popoutModuleActive: false,
                poppedOutCount: 0,
                singletonMethods: [],
                windowOpenHooked: false,
                documentWriteHooked: false,
                adoptNodeHooked: false,
                errors: []
            };
            
            try {
                // Check Foundry is ready
                debugInfo.foundryReady = typeof foundry !== 'undefined';
                
                // Check for PopoutModule - the ACTUAL class name from the source code
                if (typeof PopoutModule !== 'undefined') {
                    debugInfo.popoutModuleClassExists = true;
                    
                    if (PopoutModule.singleton) {
                        debugInfo.popoutSingletonExists = true;
                        
                        // List available methods on the singleton
                        var proto = Object.getPrototypeOf(PopoutModule.singleton);
                        debugInfo.singletonMethods = Object.getOwnPropertyNames(proto);
                        
                        // How many sheets are currently popped out
                        if (PopoutModule.singleton.poppedOut) {
                            debugInfo.poppedOutCount = PopoutModule.singleton.poppedOut.size;
                        }
                    } else {
                        debugInfo.errors.push('PopoutModule exists but singleton is null');
                    }
                } else {
                    debugInfo.errors.push('PopoutModule class is not defined in window scope');
                }
                
                // Check game.modules for the module registration
                if (typeof game !== 'undefined' && game.modules) {
                    var popoutMod = game.modules.get('popout');
                    if (popoutMod) {
                        debugInfo.popoutModuleInGame = true;
                        debugInfo.popoutModuleActive = popoutMod.active;
                    } else {
                        debugInfo.errors.push('popout not found in game.modules');
                    }
                }
                
                // Hook window.open to trace every call
                var originalOpen = window.open;
                window.__dla_window_open_calls = [];
                window.open = function(url, name, features) {
                    var callInfo = { url: url, name: name, features: features, time: Date.now() };
                    window.__dla_window_open_calls.push(callInfo);
                    console.log('[DLA DEBUG] window.open called:', JSON.stringify(callInfo));
                    var result = originalOpen.call(window, url, name, features);
                    console.log('[DLA DEBUG] window.open returned:', result ? 'valid object' : 'NULL');
                    return result;
                };
                debugInfo.windowOpenHooked = true;
                
                // Hook document.write to trace what gets written to popup
                var originalWrite = Document.prototype.write;
                window.__dla_document_writes = [];
                Document.prototype.write = function(html) {
                    var entry = { len: html ? html.length : 0, snippet: html ? html.substring(0, 200) : '' };
                    window.__dla_document_writes.push(entry);
                    console.log('[DLA DEBUG] document.write called, length:', entry.len, 'snippet:', entry.snippet);
                    return originalWrite.call(this, html);
                };
                debugInfo.documentWriteHooked = true;
                
                // Hook adoptNode to trace DOM moves between windows
                var originalAdopt = Document.prototype.adoptNode;
                window.__dla_adopt_calls = [];
                Document.prototype.adoptNode = function(node) {
                    var info = { nodeType: node ? node.nodeType : null, nodeName: node ? node.nodeName : null };
                    window.__dla_adopt_calls.push(info);
                    console.log('[DLA DEBUG] adoptNode called:', JSON.stringify(info));
                    return originalAdopt.call(this, node);
                };
                debugInfo.adoptNodeHooked = true;
                
                console.log('[DLA DEBUG] All hooks installed');
                console.log('[DLA DEBUG] PopoutModule exists:', debugInfo.popoutModuleClassExists);
                console.log('[DLA DEBUG] Singleton exists:', debugInfo.popoutSingletonExists);
                console.log('[DLA DEBUG] Module active:', debugInfo.popoutModuleActive);
                
            } catch(e) {
                debugInfo.errors.push('Exception: ' + e.message);
                console.log('[DLA DEBUG] Exception:', e.message, e.stack);
            }
            
            return JSON.stringify(debugInfo);
        })();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                
                self.log(f"\nPopOut Module Debug Information:")
                self.log(f"  Foundry ready: {data.get('foundryReady', False)}")
                self.log(f"  PopoutModule class exists: {data.get('popoutModuleClassExists', False)}")
                self.log(f"  PopoutModule.singleton exists: {data.get('popoutSingletonExists', False)}")
                self.log(f"  Module in game.modules: {data.get('popoutModuleInGame', False)}")
                self.log(f"  Module active: {data.get('popoutModuleActive', False)}")
                self.log(f"  Currently popped out: {data.get('poppedOutCount', 0)}")
                self.log(f"  window.open hooked: {data.get('windowOpenHooked', False)}")
                self.log(f"  document.write hooked: {data.get('documentWriteHooked', False)}")
                self.log(f"  adoptNode hooked: {data.get('adoptNodeHooked', False)}")
                
                methods = data.get('singletonMethods', [])
                if methods:
                    self.log(f"  Singleton methods: {', '.join(methods)}")
                
                if data.get('errors'):
                    self.log(f"\n  Errors:")
                    for err in data['errors']:
                        self.log(f"    - {err}")
                
                self.log(f"\nHooks installed. Now pop out a sheet then click 'Check PopOut Calls'.")
                
            except Exception as e:
                self.log(f"Error parsing debug result: {e}")
                self.log(f"Raw result: {result}")
        
        self.browser.page().runJavaScript(debug_script, on_result)
        
    def test_check_popout_calls(self):
        """Check what PopOut calls were captured"""
        self.log("\n--- Checking captured PopOut calls ---")
        
        check_script = """
        (function() {
            return JSON.stringify({
                windowOpenCalls: window.__popout_window_open_calls || [],
                documentWriteCalls: window.__popout_document_writes || [],
                totalWindowOpens: (window.__popout_window_open_calls || []).length,
                totalDocumentWrites: (window.__popout_document_writes || []).length
            });
        })();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                
                self.log(f"\nCaptured PopOut Calls:")
                self.log(f"  window.open() calls: {data.get('totalWindowOpens', 0)}")
                
                if data.get('windowOpenCalls'):
                    for i, call in enumerate(data['windowOpenCalls'][:5]):  # Show first 5
                        self.log(f"    [{i}] URL: {call.get('url')}, Name: {call.get('name')}")
                
                self.log(f"  document.write() calls: {data.get('totalDocumentWrites', 0)}")
                
                if data.get('documentWriteCalls'):
                    for i, call in enumerate(data['documentWriteCalls'][:5]):  # Show first 5
                        self.log(f"    [{i}] {call.get('htmlLength')} chars, at {call.get('timestamp')}")
                        
            except Exception as e:
                self.log(f"Error checking calls: {e}")
        
        self.browser.page().runJavaScript(check_script, on_result)
        
    def test_popout_workflow(self):
        """Test 3c: Test the FULL pop-out workflow"""
        self.log("\n--- TEST 3c: FULL Pop-out Workflow ---")
        self.log("This tests the ACTUAL pop-out behavior from start to finish")
        self.log("\nMANUAL STEPS REQUIRED:")
        self.log("1. Open a character sheet in the Foundry window")
        self.log("2. Click the pop-out icon on the sheet (should create new window)")
        self.log("3. Verify the character sheet appears in the new window")
        self.log("4. Look for a 'Pop In' button in the new window")
        self.log("5. Click 'Pop In' to return the sheet to the main window")
        self.log("6. Verify the sheet is back in the main window")
        self.log("7. Verify you can open the sheet again in the main window")
        self.log("\nOnce you've completed these steps, report PASS or FAIL")
        self.log("\nExpected behavior:")
        self.log("- Pop-out window opens with character sheet")
        self.log("- Pop In button exists and works")
        self.log("- Sheet can be re-opened in main window after pop in")
        self.test_results['popout_workflow'] = 'MANUAL'
        
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
