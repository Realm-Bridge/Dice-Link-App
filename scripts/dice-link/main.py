"""Dice Link - Physical dice rolling companion for Foundry VTT"""

import threading
import time
import uvicorn
import sys
import os
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QWidget, QSizePolicy
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QFontDatabase
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, Qt, QObject, pyqtSlot, pyqtSignal, QPoint, QEvent, QTimer
from PyQt6.QtWebChannel import QWebChannel
# Add the current directory to Python path so uvicorn can find app module
DICE_LINK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DICE_LINK_DIR))
os.chdir(DICE_LINK_DIR)

from config import WEBSOCKET_HOST, WEBSOCKET_PORT, APP_NAME, DEBUG, CONNECTION_METHOD
from upnp import setup_upnp_port_forward, remove_upnp_port_forward, get_external_ip
from debug import log_startup, log_server, log_drag_start, log_drag_move, log_drag_end, log_vtt
from bridge_state import set_bridge


class VTTValidator:
    """Validates if a URL points to a Foundry VTT server"""
    
    @staticmethod
    def validate_url(url: str, callback):
        """
        Check if URL is a valid Foundry VTT server.
        
        Foundry indicators:
        - Page title contains "Foundry Virtual Tabletop"
        - Has /api/status endpoint
        - Returns specific HTML structure
        """
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


class DLABridge(QObject):
    """
    Python object exposed to JavaScript via QWebChannel.
    Allows Foundry DLC module to communicate with DLA and vice versa.
    """
    
    # Signals emitted to JavaScript (names must match what DLC expects)
    rollResultReady = pyqtSignal(str)  # Emits JSON string of roll result
    rollCancelledReady = pyqtSignal(str)  # Emits JSON string with cancellation reason
    rollCompleteReady = pyqtSignal(str)  # Emits JSON string when roll is complete/acknowledged
    diceResultReady = pyqtSignal(str)  # Emits JSON string of dice result
    connectionStatusReady = pyqtSignal(str)  # Emits connection status: "connected", "disconnected", or "error"
    dlcModuleReady = pyqtSignal(str)  # Emits acknowledgement when DLC module announces it's ready
    buttonSelectReady = pyqtSignal(str)  # Emits button selection from UI to DLC
    diceTrayRollReady = pyqtSignal(str)  # Emits dice tray roll result
    playerModesUpdateReady = pyqtSignal(str)  # Emits player mode changes from DLA
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_vtt = log_vtt  # Store reference to logging function
        self.last_dlc_activity = None
        self.connection_check_timer = None
        self.log_vtt("[BRIDGE] DLABridge created")
    
    @pyqtSlot()
    def dlcModuleInitialized(self):
        """
        Called by JavaScript (DLC module) when it has loaded and initialized.
        DLC uses this to announce it's ready and establish the connection.
        """
        self.log_vtt("[BRIDGE] DLC module has initialized and announced it's ready")
        self.update_dlc_activity()
        self.start_connection_monitoring()
        
        # Emit connection status as connected (to Foundry/DLC via QWebChannel)
        self.connectionStatusReady.emit("connected")
        self.log_vtt("[BRIDGE] Emitted connectionStatusReady: connected")
        
        # Broadcast connection status to UI controls window (via Flask WebSocket)
        from bridge_state import send_connection_status_to_ui
        send_connection_status_to_ui(connected=True, player_name=None)
        
        # Emit signal to acknowledge DLC is present
        self.dlcModuleReady.emit(json.dumps({
            "type": "dlcModuleAck",
            "status": "DLA is ready to receive rolls from DLC",
            "embedded": True
        }))
    
    @pyqtSlot(str)
    def receiveRollRequest(self, data_json):
        """
        Called by JavaScript (DLC module) to send a roll request to DLA.
        
        Args:
            data_json: JSON string containing roll request data
        """
        self.update_dlc_activity()
        try:
            data = json.loads(data_json)
            request_id = data.get('id', 'unknown')
            self.log_vtt(f"[BRIDGE] Received roll request #{request_id}")
            self.log_vtt(f"[BRIDGE] Roll: {data.get('roll', {}).get('title', 'Unknown')}")
            
            # Forward to UI controls window via Flask WebSocket
            from bridge_state import send_roll_request_to_ui
            send_roll_request_to_ui(data)
            
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receiveRollRequest")
    
    @pyqtSlot(str)
    def receiveDiceRequest(self, data_json):
        """
        Called by JavaScript (DLC module) to send a dice request to DLA.
        Forwards to Flask UI to close roll request window and show dice rolling screen.
        
        Args:
            data_json: JSON string containing dice request data
        """
        self.update_dlc_activity()
        try:
            data = json.loads(data_json)
            request_id = data.get('id', 'unknown')
            self.log_vtt(f"[BRIDGE] Received dice request #{request_id}")
            
            # Forward to UI controls window to show dice rolling screen
            from bridge_state import send_dice_request_to_ui
            send_dice_request_to_ui(data)
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receiveDiceRequest")
    
    @pyqtSlot(str)
    def receivePlayerModesUpdate(self, data_json):
        """
        Called by JavaScript (DLC module) to broadcast player modes update.
        Forwards to Flask UI and extracts player name for connection status.
        
        Args:
            data_json: JSON string containing player modes data
        """
        self.update_dlc_activity()
        try:
            data = json.loads(data_json)
            self.log_vtt(f"[BRIDGE] Received player modes update")
            
            # Forward to UI controls window via Flask WebSocket
            from bridge_state import send_player_modes_to_ui, update_connection_player_name, send_connection_status_to_ui
            send_player_modes_to_ui(data)
            
            # Extract logged-in player name by looking for isSelf flag
            # data format: {"playerId": {"name": "PlayerName", "mode": "digital", "isSelf": true, ...}, ...}
            player_name = None
            for player_id, player_data in data.items():
                if isinstance(player_data, dict) and player_data.get('isSelf') is True:
                    player_name = player_data.get('name')
                    break
            
            if player_name:
                update_connection_player_name(player_name)
                # Update connection status display with the logged-in player name
                send_connection_status_to_ui(connected=True, player_name=player_name)
                self.log_vtt(f"[BRIDGE] Logged-in player: {player_name}")
            else:
                self.log_vtt("[BRIDGE] WARNING: No player found with isSelf=true in player modes data")
                    
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receivePlayerModesUpdate")
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR processing player modes: {e}")
    
    @pyqtSlot(str)
    def receiveButtonSelect(self, data_json):
        """
        Called by Flask handler when user clicks a button in the controls window.
        Forwards button selection to DLC via QWebChannel.
        
        Args:
            data_json: JSON string containing button selection data
        """
        self.update_dlc_activity()
        try:
            data = json.loads(data_json)
            roll_id = data.get('rollId')
            button = data.get('button')
            self.log_vtt(f"[BRIDGE] Received button select from UI: {button} for roll {roll_id}")
            
            # Forward to DLC via QWebChannel signal
            self.buttonSelectReady.emit(json.dumps(data))
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receiveButtonSelect")
    
    def sendRollResult(self, roll_result_data):
        """
        Called by DLA to send roll result back to Foundry DLC.
        
        Args:
            roll_result_data: Dict with roll result (will be converted to JSON)
        """
        try:
            data_json = json.dumps(roll_result_data)
            self.log_vtt(f"[BRIDGE] Sending roll result: {roll_result_data.get('id', 'unknown')}")
            self.rollResultReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending roll result: {str(e)}")
    
    def sendRollCancelled(self, request_id, reason="User cancelled"):
        """
        Called by DLA to notify Foundry that a roll was cancelled.
        
        Args:
            request_id: Original request ID
            reason: Reason for cancellation
        """
        data = {
            "type": "rollCancelled",
            "id": request_id,
            "reason": reason
        }
        try:
            data_json = json.dumps(data)
            self.log_vtt(f"[BRIDGE] Sending roll cancelled: {request_id}")
            self.rollCancelledReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending roll cancelled: {str(e)}")
    
    def sendDiceResult(self, dice_result_data):
        """
        Called by DLA to send dice result back to Foundry DLC.
        
        Args:
            dice_result_data: Dict with dice result (will be converted to JSON)
        """
        try:
            data_json = json.dumps(dice_result_data)
            self.log_vtt(f"[BRIDGE] Sending dice result: {dice_result_data.get('id', 'unknown')}")
            self.diceResultReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending dice result: {str(e)}")
    
    def notifyConnectionStatus(self, status):
        """
        Notify JavaScript of connection status changes.
        
        Args:
            status: Status string ("connected", "disconnected", "error")
        """
        self.log_vtt(f"[BRIDGE] Connection status: {status}")
        self.connectionStatusReady.emit(status)
    
    def start_connection_monitoring(self):
        """Start periodic connection status check (every 30 seconds)"""
        from PyQt6.QtCore import QTimer
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection_status)
        self.connection_check_timer.start(30000)  # 30 seconds
        self.log_vtt("[BRIDGE] Started connection monitoring (30 second interval)")
        
        # Record initial activity
        import time
        self.last_dlc_activity = time.time()
    
    def stop_connection_monitoring(self):
        """Stop the connection status check timer"""
        if self.connection_check_timer:
            self.connection_check_timer.stop()
            self.log_vtt("[BRIDGE] Stopped connection monitoring")
    
    def check_connection_status(self):
        """
        Periodically check if DLC is still connected.
        If no activity for too long, assume disconnected.
        """
        import time
        current_time = time.time()
        
        # If we haven't heard from DLC in 90 seconds, consider it disconnected
        if self.last_dlc_activity and (current_time - self.last_dlc_activity) > 90:
            self.log_vtt("[BRIDGE] Connection timeout - no activity from DLC in 90 seconds")
            self.notifyConnectionStatus("disconnected")
            # Notify UI as well
            from bridge_state import send_connection_status_to_ui
            send_connection_status_to_ui(connected=False)
            self.stop_connection_monitoring()
    
    def update_dlc_activity(self):
        """Called whenever DLC sends something - updates last activity timestamp"""
        import time
        self.last_dlc_activity = time.time()
    
    def sendRollComplete(self, roll_data):
        """
        Called by DLA to notify Foundry that a roll has been completed/acknowledged.
        
        Args:
            roll_data: Dict with roll completion data (will be converted to JSON)
        """
        try:
            data_json = json.dumps(roll_data)
            self.log_vtt(f"[BRIDGE] Sending roll complete: {roll_data.get('id', 'unknown')}")
            self.rollCompleteReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending roll complete: {str(e)}")
    
    def sendDiceTrayRoll(self, dice_tray_data):
        """
        Called by DLA to send dice tray roll result back to Foundry DLC.
        
        Args:
            dice_tray_data: Dict with dice tray roll data (will be converted to JSON)
        """
        try:
            data_json = json.dumps(dice_tray_data)
            self.log_vtt(f"[BRIDGE] Sending dice tray roll: {dice_tray_data.get('id', 'unknown')}")
            self.diceTrayRollReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending dice tray roll: {str(e)}")
    
    def sendPlayerModesUpdate(self, player_modes_data):
        """
        Called by DLA to send player modes update to Foundry DLC.
        
        Args:
            player_modes_data: Dict with player modes data (will be converted to JSON)
        """
        try:
            data_json = json.dumps(player_modes_data)
            self.log_vtt(f"[BRIDGE] Sending player modes update to DLC")
            self.playerModesUpdateReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending player modes update: {str(e)}")


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


class VTTPopupWindow(QMainWindow):
    """Window container for VTT pop-outs"""
    
    def __init__(self, web_view):
        super().__init__()
        self.web_view = web_view
        self.is_closing = False  # Flag to prevent multiple close attempts
        
        self.setWindowTitle("VTT Pop-out")
        self.resize(600, 700)
        
        self.setCentralWidget(web_view)
        
        # Update title when page title changes
        web_view.page().titleChanged.connect(self.on_title_changed)
        
        log_vtt("[POPUP] Window created")
    
    def on_title_changed(self, title):
        if title and title != "about:blank":
            self.setWindowTitle(title)

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
                from PyQt6.QtCore import QTimer
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


class CustomViewerTitleBar(QWidget):
    """Custom title bar for VTT Viewing Window matching DLA main window style"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.drag_position = None
        
        # Set fixed height for title bar
        self.setFixedHeight(40)
        
        # Style matching DLA main window colors
        self.setStyleSheet("""
            QWidget {
                background-color: #0f1419;
            }
            QLabel {
                color: #f0f2f5;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #6f2e9a;
                font-size: 28px;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.1);
            }
            QPushButton#closeBtn:hover {
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444;
            }
        """)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        
        # Dice Link logo (left side)
        self.dice_link_logo = QLabel()
        logo_path = DICE_LINK_DIR / "static" / "Logos" / "DL_Logo_No_Background.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            scaled_pixmap = pixmap.scaledToHeight(44, Qt.TransformationMode.SmoothTransformation)
            self.dice_link_logo.setPixmap(scaled_pixmap)
        layout.addWidget(self.dice_link_logo)
        
        # Spacer
        layout.addStretch()
        
        # Window control buttons (right side)
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(36, 36)
        self.minimize_btn.clicked.connect(self.minimize_window)
        layout.addWidget(self.minimize_btn)
        
        self.maximize_btn = QPushButton("O")
        self.maximize_btn.setFixedSize(36, 36)
        rubik_font = QFont("Rubik", 18)
        rubik_font.setBold(True)
        self.maximize_btn.setFont(rubik_font)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.maximize_btn)
        
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(36, 36)
        self.close_btn.clicked.connect(self.close_window)
        layout.addWidget(self.close_btn)
    
    def minimize_window(self):
        if self.parent_window:
            self.parent_window.showMinimized()
    
    def toggle_maximize(self):
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_btn.setText("O")
            else:
                self.parent_window.showMaximized()
                self.maximize_btn.setText("o")
    
    def close_window(self):
        if self.parent_window:
            self.parent_window.close()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.drag_position = None


class ResizeGrip(QWidget):
    """Invisible resize grip widget for handling window resizing"""
    
    def __init__(self, parent, resize_direction, grip_size=16):
        super().__init__(parent)
        self.parent_window = parent
        self.resize_direction = resize_direction
        self.resize_start_pos = None
        self.resize_start_geometry = None
        
        self.setFixedSize(grip_size, grip_size)
        self.setStyleSheet("background-color: transparent;")
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if "diagonal" in resize_direction else Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_start_pos = event.globalPosition().toPoint()
            self.resize_start_geometry = self.parent_window.geometry()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.resize_start_pos:
            diff = event.globalPosition().toPoint() - self.resize_start_pos
            geo = self.resize_start_geometry
            new_geo = self.parent_window.geometry()
            
            if "right" in self.resize_direction:
                new_geo.setRight(geo.right() + diff.x())
            if "bottom" in self.resize_direction:
                new_geo.setBottom(geo.bottom() + diff.y())
            
            if new_geo.width() >= self.parent_window.minimumWidth() and new_geo.height() >= self.parent_window.minimumHeight():
                self.parent_window.setGeometry(new_geo)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.resize_start_pos = None
        self.resize_start_geometry = None


class VTTViewingWindow(QMainWindow):
    """Main viewing window for VTT - closes all popups when closed"""
    
    def __init__(self, vtt_view):
        super().__init__()
        self.vtt_view = vtt_view
        
        # Make window frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(400, 300)
        
        # Create central widget to hold title bar and content
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #0f1419;")
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add custom title bar
        self.title_bar = CustomViewerTitleBar(self)
        # Prevent cursor changes and event propagation for title bar
        self.title_bar.setCursor(Qt.CursorShape.ArrowCursor)
        self.title_bar.setMouseTracking(False)
        main_layout.addWidget(self.title_bar)
        
        # Add the VTT view
        main_layout.addWidget(vtt_view)
        
        # Add invisible resize grip for bottom-right corner
        self.resize_grip = ResizeGrip(self, "bottom-right-diagonal", grip_size=16)
        self.resize_grip.raise_()
        
        log_vtt("[VIEWER] Viewing window created with custom title bar and resize grip")
    
    def resizeEvent(self, event):
        """Reposition resize grip when window is resized"""
        super().resizeEvent(event)
        if hasattr(self, 'resize_grip'):
            # Position grip at bottom-right corner
            grip_size = self.resize_grip.width()
            self.resize_grip.move(
                self.width() - grip_size,
                self.height() - grip_size
            )
    
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


class ConnectionDialog(QDialog):
    """Dialog for entering and validating VTT server URL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to VTT Server")
        self.setMinimumWidth(400)
        self.vtt_url = None
        self.is_validating = False
        
        # Create layout
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Enter VTT Server URL:")
        layout.addWidget(label)
        
        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:30000 or https://example.com")
        layout.addWidget(self.url_input)
        
        # Error message label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ff6b6b;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        button_layout.addWidget(self.connect_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_connect(self):
        """Handle connect button click - validate the URL"""
        url = self.url_input.text().strip()
        
        if not url:
            self.show_error("Please enter a URL")
            return
        
        # Store the URL being validated
        self.validating_url = url
        
        # Update UI state
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Validating...")
        self.error_label.setVisible(False)
        
        # Validate URL (synchronous - callback called directly)
        VTTValidator.validate_url(url, self.on_validation_complete)
    
    def on_validation_complete(self, is_valid, message, data):
        """Handle validation result"""
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        
        if is_valid:
            self.vtt_url = self.validating_url
            self.accept()
        else:
            self.show_error(message)
    
    def show_error(self, message):
        """Display error message"""
        self.error_label.setText(f"Error: {message}")
        self.error_label.setVisible(True)


class WindowController(QObject):
    """Handles window control commands from JavaScript"""
    
    def __init__(self, browser, main_window=None):
        super().__init__()
        self.browser = browser
        self.main_window = main_window  # Reference to main application window
        self.mouse_offset = QPoint()  # Offset from mouse to window corner
    
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
        # JavaScript sends screenX/screenY (global screen coordinates)
        global_mouse_pos = QPoint(x, y)
        window_pos = self.browser.pos()
        # Store offset: how far from window corner the mouse clicked
        self.mouse_offset = window_pos - global_mouse_pos
    
    @pyqtSlot(int, int)
    def doDrag(self, x, y):
        """Perform window drag - move window so mouse stays at same relative position"""
        if self.mouse_offset.isNull():
            return
        # JavaScript sends screenX/screenY (global screen coordinates)
        global_mouse_pos = QPoint(x, y)
        # Window position = mouse position + stored offset
        new_window_pos = global_mouse_pos + self.mouse_offset
        self.browser.move(new_window_pos)
    
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


class DraggableWebEngineView(QWebEngineView):
    """Custom QWebEngineView with frameless window dragging support"""
    
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.is_dragging = False
        self.window_controller = None  # Will be set after creation
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        # Check if click is in title bar area (top 80px)
        if event.position().y() < 80:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            log_drag_start(event.globalPosition(), self.drag_position, self.pos())
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging"""
        if self.is_dragging:
            global_pos_float = event.globalPosition()
            global_pos_int = global_pos_float.toPoint()
            calculated_pos = global_pos_int - self.drag_position
            current_window_pos = self.pos()
            log_drag_move(global_pos_float, global_pos_int, self.drag_position, calculated_pos, current_window_pos)
            self.move(calculated_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.is_dragging = False
        log_drag_end()
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        # F12 prints DevTools URL to console
        if event.key() == Qt.Key.Key_F12:
            print("[DevTools] Open http://localhost:9222 in a browser to debug")
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle main window close - close all child VTT windows"""
        if self.window_controller and hasattr(self.window_controller, 'vtt_windows'):
            # Close all VTT windows
            for vtt_window in self.window_controller.vtt_windows:
                vtt_window.close()
        
        # Allow the main window to close
        event.accept()


def run_server():
    """Run the FastAPI server in a background thread"""
    uvicorn.run(
        "server:app",
        host=WEBSOCKET_HOST,
        port=WEBSOCKET_PORT,
        reload=False,
        log_level="info" if DEBUG else "warning"
    )


def main():
    """Main entry point for Dice Link - launches desktop app with PyQt5"""
    # Print startup banner
    print(f"\n{'='*50}")
    print(f"  {APP_NAME}")
    print(f"  Physical dice rolling for Foundry VTT")
    print(f"{'='*50}\n")
    
    log_server("Starting Dice Link Desktop App...")
    log_startup(WEBSOCKET_HOST, WEBSOCKET_PORT)
    log_server(f"Server running on http://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    log_server(f"UI available at http://localhost:{WEBSOCKET_PORT}")
    
    # Show connection method info
    if CONNECTION_METHOD == "webrtc":
        log_server(f"Connection method: WebRTC (bypasses browser security restrictions)")
        log_server(f"DLC connects via WebRTC handshake at http://localhost:{WEBSOCKET_PORT}/api/receive-offer")
    else:
        log_server(f"Connection method: WebSocket (fallback mode)")
        log_server(f"DLC module connects to ws://[hostname]:{WEBSOCKET_PORT}/ws/dlc")
    
    # UPnP is only relevant for WebSocket fallback mode (remote connections)
    # For WebRTC on localhost, no port forwarding is needed
    upnp_success = False
    external_ip = None
    if CONNECTION_METHOD == "websocket":
        # Attempt UPnP port forwarding for remote connections
        upnp_success, external_ip = setup_upnp_port_forward(WEBSOCKET_PORT)
        if upnp_success:
            log_server("Remote connections enabled!")
            log_server(f"Players should configure DLC to connect to: {external_ip}")
        else:
            if external_ip:
                log_server("Automatic port forwarding unavailable")
                log_server(f"Your external IP is: {external_ip}")
                log_server(f"For remote connections, manually forward port {WEBSOCKET_PORT} in your router")
            else:
                log_server("Could not determine external IP or set up port forwarding")
                log_server("Remote connections may require manual router configuration")
    else:
        log_server("UPnP skipped (not needed for localhost WebRTC connections)")
    
    # Start the FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(1.5)
    
    # Create and display the PyQt6 window
    app = QApplication(sys.argv)
    
    # Enable DevTools via environment variable - must be set before creating the profile
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
    
    # Create profile with devtools enabled
    profile = QWebEngineProfile.defaultProfile()
    
    # Create a draggable web view widget
    browser = DraggableWebEngineView()
    browser.setPage(browser.page())  # Ensure page is initialized
    
    # Enable transparent background for rounded corners
    browser.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    
    # Set up window controller for frameless window control
    window_controller = WindowController(browser, browser)
    browser.window_controller = window_controller  # Store reference for closeEvent
    
    # Set window properties
    browser.setWindowTitle(APP_NAME)
    browser.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    
    # Set up web channel for JavaScript-to-Python communication
    channel = QWebChannel()
    channel.registerObject("pyqtBridge", window_controller)
    browser.page().setWebChannel(channel)
    
    # Lock window to fixed size - cannot be resized
    # Original planned size - will be scaled by device pixel ratio
    fixed_width = 1788
    fixed_height = 1500
    
    # Store fixed size and browser reference for dynamic scaling
    browser.fixed_width = fixed_width
    browser.fixed_height = fixed_height
    
    # Function to update scaling when DPI changes
    def update_dpi_scaling():
        screen = browser.screen()
        device_pixel_ratio = screen.devicePixelRatio() if screen else 1.0
        
        # Calculate scaled window size
        scaled_width = int(browser.fixed_width / device_pixel_ratio)
        scaled_height = int(browser.fixed_height / device_pixel_ratio)
        
        # Update window size
        browser.setFixedSize(scaled_width, scaled_height)
        
        # Update zoom factor - inverse of device ratio so content scales DOWN with window
        # If device ratio is 2.0 (200% scaling), zoom should be 0.5 to fit content in half-sized window
        browser.setZoomFactor(1.0 / device_pixel_ratio)
        
        print(f"[DPI UPDATE] Device pixel ratio: {device_pixel_ratio}, Window size: {scaled_width}x{scaled_height}")
    
    # Initial scaling
    update_dpi_scaling()
    
    # Connect to screen DPI changes
    screen = browser.screen()
    if screen:
        screen.logicalDotsPerInchChanged.connect(update_dpi_scaling)
        # If window moves to different display, also update scaling
        screen.geometryChanged.connect(update_dpi_scaling)
    
    # Load the local server URL (always use localhost for browser, even if server binds to 0.0.0.0)
    browser_host = "localhost" if WEBSOCKET_HOST == "0.0.0.0" else WEBSOCKET_HOST
    url = f"http://{browser_host}:{WEBSOCKET_PORT}"
    browser.load(QUrl(url))
    
    # Show the window and start the application
    browser.show()
    
    # Run the application
    exit_code = app.exec()
    
    # Clean up UPnP port forwarding on exit
    if upnp_success:
        log_server("Cleaning up port forwarding...")
        remove_upnp_port_forward(WEBSOCKET_PORT)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


