from PyQt6.QtCore import QTimer, QUrl
from custom_window import CustomWindow
from debug import log_vtt


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
        super().__init__(show_maximize=True, resizable=True, title="DLA Viewer")
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
