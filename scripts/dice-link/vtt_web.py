import json
from urllib.parse import urlparse

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebChannel, QWebEngineSettings, QWebEnginePage
from PyQt6.QtCore import QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QPoint

from debug import log_vtt
from bridge_state import set_bridge
from dla_bridge import DLABridge
from custom_window import CustomWindow


class VTTWebPage(QWebEnginePage):
    """Custom web page - only blocks external navigation"""
    
    def __init__(self, profile, allowed_origin, parent=None):
        super().__init__(profile, parent)
        self.allowed_origin = allowed_origin
    
    def javaScriptConsoleMessage(self, level, message, line, source):
        """Capture ALL JavaScript console output and display in our log"""
        try:
            # level is a JavaScriptConsoleMessageLevel enum, convert to int
            level_int = int(level)
            level_str = {0: "INFO", 1: "WARN", 2: "ERROR"}.get(level_int, "LOG")
            
            # Only log messages that seem relevant (errors, our debug, or PopOut related)
            if level_int >= 1 or "DLA" in message or "POPOUT" in message or "SIMULATE" in message or "error" in message.lower() or "Error" in message:
                log_vtt(f"[JS {level_str}] {message}")
                if level_int >= 2:  # For errors, also show source info
                    log_vtt(f"  Source: {source}, Line: {line}")
        except Exception as e:
            log_vtt(f"[Console Error] {message}")
        
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
        
        log_vtt(f"\nBLOCKED: External navigation to {url_str}")
        return False


class VTTPopupWindow(CustomWindow):
    """Window container for VTT pop-outs with custom title bar styling"""
    
    def __init__(self, web_view):
        super().__init__(show_maximize=True, resizable=True, title="VTT Pop-out")
        self.web_view = web_view
        self.is_closing = False  # Flag to prevent multiple close attempts
        
        self.resize(600, 700)
        
        # Add the web view to the content area
        self.content_layout.addWidget(web_view)
        
        # Update title when page title changes
        web_view.page().titleChanged.connect(self.on_title_changed)
        
        log_vtt("[POPUP] Window created with custom title bar styling")
    
    def on_title_changed(self, title):
        if title and title != "about:blank":
            self.setWindowTitle(title)
            self.title_bar.set_title(title)

    def closeEvent(self, event):
        """Intercept OS close button - trigger the sheet's own close button instead"""
        if self.is_closing:
            # Already processing close, allow it this time
            log_vtt("[POPUP] Close already in progress, allowing close")
            event.accept()
            return
        
        log_vtt("[POPUP] OS close button clicked - triggering sheet close button")
        self.is_closing = True
        
        # Click the sheet's close button so PopOut module returns the sheet properly
        trigger_script = """
        (function() {
            var closeBtn = document.querySelector('[data-action="close"]');
            if (closeBtn) {
                console.log('[POPUP] Found close button, clicking it');
                closeBtn.click();
                return 'clicked';
            } else {
                console.log('[POPUP] Close button not found');
                return 'not_found';
            }
        })();
        """
        
        def on_result(result):
            log_vtt(f"[POPUP] Trigger close button result: {result}")
            if result == 'clicked':
                # Sheet button was clicked, wait a moment for the page to unload, then close the window
                log_vtt("[POPUP] Sheet button clicked, waiting for unload...")
                # Use a timer to wait for the unload to complete
                QTimer.singleShot(500, self.perform_close)
            else:
                # No sheet button found - close immediately
                log_vtt("[POPUP] No sheet button, closing window directly")
                self.perform_close()
        
        self.web_view.page().runJavaScript(trigger_script, on_result)
        
        # Ignore the close event for now - we'll call perform_close() when ready
        event.ignore()
    
    def perform_close(self):
        """Actually close the window"""
        log_vtt("[POPUP] Performing window close")
        self.close()  # This will call closeEvent again, but is_closing flag will allow it


class VTTViewingWindow(CustomWindow):
    """Main viewing window for VTT - closes all popups when closed"""
    
    def __init__(self, vtt_view):
        super().__init__(show_maximize=True, resizable=True)
        self.vtt_view = vtt_view
        
        self.setGeometry(100, 100, 1200, 800)
        
        # Add the VTT view into the content area
        self.content_layout.addWidget(vtt_view)
        
        log_vtt("[VIEWER] Viewing window created with custom title bar and resize grip")
    
    def closeEvent(self, event):
        """Close all popup windows and disconnect from VTT when viewing window closes"""
        log_vtt("[VIEWER] Viewing window closing - closing all popups and disconnecting")
        
        # Close all popup windows created by this viewing window
        if hasattr(self.vtt_view, 'popup_windows'):
            for popup_window in self.vtt_view.popup_windows:
                log_vtt("[VIEWER] Closing popup window")
                popup_window.close()
        
        # Stop connection monitoring
        if hasattr(self.vtt_view, 'dla_bridge') and self.vtt_view.dla_bridge:
            self.vtt_view.dla_bridge.stop_connection_monitoring()
            # Notify UI that connection is lost
            from bridge_state import send_connection_status_to_ui
            send_connection_status_to_ui(connected=False)
        
        # Disconnect from Foundry by stopping page and navigating away
        log_vtt("[VIEWER] Disconnecting from VTT")
        self.vtt_view.stop()
        self.vtt_view.setUrl(QUrl("about:blank"))
        
        # Clean up the page to fully release the connection
        if self.vtt_view.page():
            self.vtt_view.page().deleteLater()
        
        # Allow the viewing window to close
        event.accept()


class VTTWebView(QWebEngineView):
    """
    Custom WebEngineView that properly handles window.open() by overriding createWindow().
    
    This is the KEY fix: when JavaScript calls window.open(), Qt calls createWindow()
    and the RETURNED view becomes the popup. JavaScript gets a reference to this window,
    which is what Foundry's PopOut module needs.
    """
    
    def __init__(self, allowed_origin, parent=None):
        super().__init__(parent)
        self.allowed_origin = allowed_origin
        self.popup_windows = []  # Keep references to prevent garbage collection
        
        # Set custom page for navigation blocking
        self.custom_page = VTTWebPage(self.page().profile(), allowed_origin)
        self.setPage(self.custom_page)
        
        # Configure WebEngine settings (required for QWebChannel and JavaScript to work)
        settings = self.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        
        # Setup QWebChannel bridge for DLC communication
        self.setup_webchannel()
        
        # Inject QWebChannel when page loads
        self.page().loadFinished.connect(self.on_page_loaded)
    
    def setup_webchannel(self):
        """Setup QWebChannel with DLABridge object"""
        # Create the channel
        self.channel = QWebChannel()
        
        # Create the DLA bridge object
        self.dla_bridge = DLABridge()
        
        # Register the bridge globally so Flask can access it
        set_bridge(self.dla_bridge)
        
        # Register the bridge - will be accessible as 'dlaInterface' in JS
        self.channel.registerObject("dlaInterface", self.dla_bridge)
        
        # Attach channel to the page
        self.page().setWebChannel(self.channel)
        
        log_vtt("[WEBCHANNEL] QWebChannel created and DLABridge registered as 'dlaInterface'")
    
    def on_page_loaded(self, ok):
        """Called when page finishes loading - inject qwebchannel.js"""
        if not ok:
            log_vtt("[WEBCHANNEL] Page load failed")
            return
        
        log_vtt("[WEBCHANNEL] Page loaded, injecting QWebChannel.js...")
        
        # First inject the qwebchannel.js library
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
            log_vtt(f"[WEBCHANNEL] QWebChannel.js load result: {result}")
            # Try to initialize the channel - if QWebChannel isn't ready yet, retry
            self.attempt_initialize_webchannel(attempt=1, max_attempts=10)
        
        self.page().runJavaScript(load_qwebchannel_js, on_qwebchannel_loaded)
    
    def attempt_initialize_webchannel(self, attempt=1, max_attempts=10):
        """
        Try to initialize QWebChannel. If QWebChannel is not defined yet, retry with backoff.
        This handles timing issues on fresh page loads where qwebchannel.js takes time to load.
        """
        # First, check if QWebChannel is available
        check_script = "typeof QWebChannel !== 'undefined'"
        
        def on_check_result(is_available):
            if is_available:
                # QWebChannel is ready, initialize now
                log_vtt(f"[WEBCHANNEL] QWebChannel detected (attempt {attempt}), initializing...")
                self.initialize_webchannel()
            elif attempt < max_attempts:
                # QWebChannel not ready yet, retry with exponential backoff
                wait_ms = min(50 * attempt, 500)  # Cap at 500ms
                log_vtt(f"[WEBCHANNEL] QWebChannel not ready (attempt {attempt}/{max_attempts}), retrying in {wait_ms}ms...")
                
                # Schedule retry
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self.attempt_initialize_webchannel(attempt + 1, max_attempts))
                timer.start(wait_ms)
                
                # Keep reference to prevent garbage collection
                if not hasattr(self, '_init_timers'):
                    self._init_timers = []
                self._init_timers.append(timer)
            else:
                # Max attempts reached
                log_vtt(f"[WEBCHANNEL] ERROR: QWebChannel still not available after {max_attempts} attempts")
        
        self.page().runJavaScript(check_script, on_check_result)
    
    def initialize_webchannel(self):
        """Initialize the QWebChannel in JavaScript and expose dlaInterface"""
        inject_script = """
        (function() {
            // Check if qt.webChannelTransport exists (Qt's internal transport)
            if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                console.error('[DLA] qt.webChannelTransport not available!');
                return JSON.stringify({
                    success: false,
                    error: 'qt.webChannelTransport not available',
                    hasQt: typeof qt !== 'undefined'
                });
            }
            
            // Load QWebChannel using Qt's internal transport (NOT WebSocket!)
            new QWebChannel(qt.webChannelTransport, function(channel) {
                // Make the DLA bridge globally accessible
                window.dlaInterface = channel.objects.dlaInterface;
                
                // Set flag indicating interface is ready
                window.dlaInterfaceReady = true;
                
                console.log('[DLA] QWebChannel initialized successfully!');
                console.log('[DLA] dlaInterface available:', typeof window.dlaInterface);
                console.log('[DLA] Waiting for DLC module to announce it is ready...');
                
                // Connect to signals from DLA
                if (window.dlaInterface) {
                    if (window.dlaInterface.rollResultReady) {
                        window.dlaInterface.rollResultReady.connect(function(resultJson) {
                            console.log('[DLA] Received roll result from Python');
                        });
                    }
                    if (window.dlaInterface.rollCancelled) {
                        window.dlaInterface.rollCancelled.connect(function(cancelJson) {
                            console.log('[DLA] Received roll cancelled from Python');
                        });
                    }
                    if (window.dlaInterface.diceResultReady) {
                        window.dlaInterface.diceResultReady.connect(function(diceJson) {
                            console.log('[DLA] Received dice result from Python');
                        });
                    }
                    if (window.dlaInterface.dlcModuleReady) {
                        window.dlaInterface.dlcModuleReady.connect(function(ackJson) {
                            console.log('[DLA] DLC module acknowledged by Python:', ackJson);
                        });
                    }
                }
            });
            
            return JSON.stringify({
                success: true,
                hasQt: true,
                hasTransport: true
            });
        })();
        """
        
        def on_channel_initialized(result):
            log_vtt(f"[WEBCHANNEL] Channel initialization result: {result}")
            if result and 'success' in str(result):
                log_vtt("[WEBCHANNEL] SUCCESS: QWebChannel initialized!")
            else:
                log_vtt("[WEBCHANNEL] WARNING: Channel may not be fully initialized")
        
        self.page().runJavaScript(inject_script, on_channel_initialized)
    
    def createWindow(self, window_type):
        """
        Override createWindow - called when JavaScript uses window.open().
        
        Create popup and inject JavaScript to expose document operations properly.
        """
        log_vtt(f"\n--- createWindow() called ---")
        log_vtt(f"Window type: {window_type}")
        
        # Create popup view that shares the SAME profile as the main page
        popup_view = QWebEngineView()
        popup_page = VTTWebPage(self.page().profile(), self.allowed_origin, popup_view)
        popup_view.setPage(popup_page)
        
        # Inject JavaScript into popup to expose document operations
        # This allows PopOut module's document.open/write/close to work
        expose_document_script = """
        (function() {
            // Ensure the popup exposes itself properly as a window
            window.__popupReady = true;
            console.log('[POPUP] Popup initialized, document available');
        })();
        """
        popup_page.runJavaScript(expose_document_script)
        
        # Create window container
        popup_window = VTTPopupWindow(popup_view)
        popup_window.show()
        
        # Keep references
        self.popup_windows.append(popup_window)
        
        log_vtt("Popup created and document exposed to JavaScript")
        
        # Return the page (not view) - this gives JavaScript a proper document interface
        # Actually, we need to return something JavaScript can interact with
        # For now return the view - Qt should handle mapping window.open() return value
        return popup_view


class VTTPopupView(QWebEngineView):
    """WebEngineView for popup windows - can create nested popups if needed"""
    
    def __init__(self, allowed_origin, parent=None):
        super().__init__(parent)
        self.allowed_origin = allowed_origin
        self.popup_windows = []
        
        # Set custom page with navigation restrictions
        self.custom_page = VTTWebPage(self.page().profile(), allowed_origin)
        self.setPage(self.custom_page)
    
    def createWindow(self, window_type):
        """Allow nested popups with same restrictions"""
        log_vtt(f"[POPUP] Nested createWindow() called")
        
        popup_view = VTTPopupView(self.allowed_origin)
        popup_window = VTTPopupWindow(popup_view)
        popup_window.show()
        self.popup_windows.append(popup_window)
        
        return popup_view
