from PyQt6.QtWidgets import QDialog
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QObject, QPoint, pyqtSlot, QUrl

from dialogs import ConnectionDialog
from vtt_web import VTTWebView
from vtt_windows import VTTViewingWindow


class WindowController(QObject):
    """Handles window control commands from JavaScript"""
    
    def __init__(self, browser, main_window=None):
        super().__init__()
        self.browser = browser
        self.main_window = main_window
        self.mouse_offset = QPoint()
        self._resize_start_mouse = None
        self._resize_start_geometry = None
    
    @pyqtSlot()
    def minimize(self):
        """Minimize the window"""
        self.browser.showMinimized()
    
    @pyqtSlot()
    def close(self):
        """Close the application"""
        self.browser.close()
    
    @pyqtSlot(int, int)
    def startDrag(self, x, y):
        """Start window drag - calculate offset from mouse to window corner"""
        global_mouse_pos = QPoint(x, y)
        window_pos = self.browser.pos()
        self.mouse_offset = window_pos - global_mouse_pos

    @pyqtSlot(int, int)
    def doDrag(self, x, y):
        """Perform window drag - move window so mouse stays at same relative position"""
        if self.mouse_offset.isNull():
            return
        global_mouse_pos = QPoint(x, y)
        new_window_pos = global_mouse_pos + self.mouse_offset
        self.browser.move(new_window_pos)

    @pyqtSlot(int, int)
    def startResize(self, x, y):
        """Start window resize - record initial mouse position and window geometry"""
        self._resize_start_mouse = QPoint(x, y)
        self._resize_start_geometry = self.browser.geometry()

    @pyqtSlot(int, int)
    def doResize(self, x, y):
        """Resize window - width follows mouse, height derived from aspect ratio"""
        if self._resize_start_mouse is None or self._resize_start_geometry is None:
            return
        diff = QPoint(x, y) - self._resize_start_mouse
        geo = self._resize_start_geometry
        new_width = max(geo.width() + diff.x(), self.browser.minimumWidth())
        designed_w = getattr(self.browser, '_designed_width', None)
        designed_h = getattr(self.browser, '_designed_height', None)
        if designed_w and designed_h:
            new_height = int(new_width * designed_h / designed_w)
        else:
            new_height = geo.height() + diff.y()
        self.browser.resize(new_width, new_height)

    @pyqtSlot()
    def openConnectionDialog(self):
        """Open connection dialog to enter VTT server URL"""
        dialog = ConnectionDialog(self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.vtt_url:
            # Launch VTT viewing window
            self.launch_vtt_window(dialog.vtt_url)
    
    def launch_vtt_window(self, url):
        """Launch a new window to view the VTT"""
        # Store reference to prevent garbage collection
        if not hasattr(self, 'vtt_windows'):
            self.vtt_windows = []
        
        allowed_origin = url.rstrip('/')
        
        # Create VTT web view with allowed origin
        vtt_view = VTTWebView(allowed_origin)
        
        # Create viewing window (which will close all popups when closed)
        vtt_window = VTTViewingWindow(vtt_view)
        
        # Load the URL
        vtt_view.load(QUrl(url))
        
        vtt_window.show()
        
        # Keep reference
        self.vtt_windows.append(vtt_window)
    
    @pyqtSlot(str)
    def openUrl(self, url):
        """Open URL in system default browser"""
        QDesktopServices.openUrl(QUrl(url))
