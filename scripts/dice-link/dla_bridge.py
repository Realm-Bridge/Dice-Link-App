"""DLABridge - QWebChannel bridge for communication between DLA and DLC."""

import json
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from debug import log_vtt, log_connection_monitor


class DLABridge(QObject):
    """
    Python object exposed to JavaScript via QWebChannel.
    Allows Foundry DLC module to communicate with DLA and vice versa.
    """

    # Signals emitted to JavaScript (names must match what DLC expects)
    rollResultReady = pyqtSignal(str)
    rollCancelledReady = pyqtSignal(str)
    rollCompleteReady = pyqtSignal(str)
    diceResultReady = pyqtSignal(str)
    connectionStatusReady = pyqtSignal(str)
    dlcModuleReady = pyqtSignal(str)
    buttonSelectReady = pyqtSignal(str)
    diceTrayRollReady = pyqtSignal(str)
    playerModesUpdateReady = pyqtSignal(str)
    connectionPingReady = pyqtSignal()
    cameraFrameReady = pyqtSignal(str)
    cameraStreamEndReady = pyqtSignal()

    PING_INTERVAL_MS = 30000  # Send ping after 30s of silence from DLC
    PONG_TIMEOUT_MS = 2000    # Declare dead if no pong within 2s

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_vtt = log_vtt
        self._is_connected = False
        self.pending_pong = False
        self.connection_check_timer = None
        self.pong_timeout_timer = None
        self.log_vtt("[BRIDGE] DLABridge created")

    # -------------------------------------------------------------------------
    # Internal connection state helpers
    # -------------------------------------------------------------------------

    def _set_connected(self):
        """Mark connection as active and notify all listeners. No-op if already connected."""
        if not self._is_connected:
            self._is_connected = True
            self.notifyConnectionStatus("connected")
            self.log_vtt("[BRIDGE] Emitted connectionStatusReady: connected")
            from bridge_state import send_connection_status_to_ui
            send_connection_status_to_ui(connected=True, player_name=None)

    def _set_disconnected(self):
        """Mark connection as dead and notify all listeners. No-op if already disconnected."""
        if self._is_connected:
            self._is_connected = False
            self.notifyConnectionStatus("disconnected")
            from bridge_state import send_connection_status_to_ui
            send_connection_status_to_ui(connected=False)

    def _reset_ping_timer(self):
        """Restart the idle countdown on any incoming message from DLC."""
        if self.connection_check_timer and self.connection_check_timer.isActive():
            self.connection_check_timer.start(self.PING_INTERVAL_MS)

    # -------------------------------------------------------------------------
    # Slots called by DLC (JavaScript → Python)
    # -------------------------------------------------------------------------

    @pyqtSlot()
    def dlcModuleInitialized(self):
        """Called by DLC when it has loaded and initialized."""
        self.log_vtt("[BRIDGE] DLC module has initialized and announced it's ready")
        self.start_connection_monitoring()
        self._set_connected()
        self.dlcModuleReady.emit(json.dumps({
            "type": "dlcModuleAck",
            "status": "DLA is ready to receive rolls from DLC",
            "embedded": True
        }))

    @pyqtSlot()
    def receiveConnectionPong(self):
        """Called by DLC in response to our ping."""
        log_connection_monitor("Received pong from DLC - connection is active")
        self.pending_pong = False
        if self.pong_timeout_timer:
            self.pong_timeout_timer.stop()
        self._reset_ping_timer()
        self._set_connected()  # no-op if already connected; reconnects if recovering

    @pyqtSlot(str)
    def receiveRollRequest(self, data_json):
        """Called by DLC to send a roll request to DLA."""
        self._reset_ping_timer()
        try:
            data = json.loads(data_json)
            request_id = data.get('id', 'unknown')
            self.log_vtt(f"[BRIDGE] Received roll request #{request_id}")
            self.log_vtt(f"[BRIDGE] Roll: {data.get('roll', {}).get('title', 'Unknown')}")
            from bridge_state import send_roll_request_to_ui
            send_roll_request_to_ui(data)
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receiveRollRequest")

    @pyqtSlot(str)
    def receiveDiceRequest(self, data_json):
        """Called by DLC to send a dice request to DLA."""
        self._reset_ping_timer()
        try:
            data = json.loads(data_json)
            request_id = data.get('id', 'unknown')
            self.log_vtt(f"[BRIDGE] Received dice request #{request_id}")
            from state import app_state
            app_state.camera_stream_armed = True
            self.log_vtt("[BRIDGE] Camera stream armed - waiting for roll")
            from bridge_state import send_dice_request_to_ui
            send_dice_request_to_ui(data)
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receiveDiceRequest")

    @pyqtSlot(str)
    def receivePlayerModesUpdate(self, data_json):
        """Called by DLC to broadcast player modes update."""
        self._reset_ping_timer()
        try:
            data = json.loads(data_json)
            self.log_vtt("[BRIDGE] Received player modes update")
            from bridge_state import send_player_modes_to_ui, update_connection_player_name, send_connection_status_to_ui

            send_player_modes_to_ui(data)

            player_name = None
            for player_id, player_data in data.items():
                if isinstance(player_data, dict) and player_data.get('isSelf') is True:
                    player_name = player_data.get('name')
                    break

            if player_name:
                update_connection_player_name(player_name)
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
        """Called by FastAPI handler when user clicks a button in the controls window.
        Not called by DLC — does not reset the ping timer."""
        try:
            data = json.loads(data_json)
            roll_id = data.get('rollId')
            button = data.get('button')
            self.log_vtt(f"[BRIDGE] Received button select from UI: {button} for roll {roll_id}")
            self.buttonSelectReady.emit(json.dumps(data))
        except json.JSONDecodeError:
            self.log_vtt("[BRIDGE] ERROR: Invalid JSON in receiveButtonSelect")

    # -------------------------------------------------------------------------
    # Connection monitoring
    # -------------------------------------------------------------------------

    def start_connection_monitoring(self):
        """Start ping/pong monitoring. If already running, resets the idle timer."""
        if self.connection_check_timer and self.connection_check_timer.isActive():
            self.connection_check_timer.start(self.PING_INTERVAL_MS)
            log_connection_monitor("Connection monitoring already active - idle timer reset")
            return

        self.pending_pong = False

        self.pong_timeout_timer = QTimer()
        self.pong_timeout_timer.setSingleShot(True)
        self.pong_timeout_timer.timeout.connect(self._handle_pong_timeout)

        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.send_connection_ping)
        self.connection_check_timer.start(self.PING_INTERVAL_MS)

        log_connection_monitor(
            f"Started connection monitoring - ping after {self.PING_INTERVAL_MS // 1000}s idle, "
            f"{self.PONG_TIMEOUT_MS // 1000}s pong timeout"
        )

    def stop_connection_monitoring(self):
        """Stop all connection monitoring timers."""
        if self.connection_check_timer:
            self.connection_check_timer.stop()
        if self.pong_timeout_timer:
            self.pong_timeout_timer.stop()
        self.log_vtt("[BRIDGE] Stopped connection monitoring")
        log_connection_monitor("Stopped connection monitoring")

    def send_connection_ping(self):
        """Send a ping to DLC and start the 2-second pong timeout."""
        log_connection_monitor("Sending ping to DLC, expecting pong within 2 seconds")
        self.pending_pong = True
        self.connectionPingReady.emit()
        self.pong_timeout_timer.start(self.PONG_TIMEOUT_MS)

    def _handle_pong_timeout(self):
        """Called 2 seconds after a ping if no pong was received."""
        if self.pending_pong:
            log_connection_monitor("TIMEOUT - No pong received within 2 seconds, connection appears dead")
            self.log_vtt("[BRIDGE] Connection timeout - DLC did not respond to ping")
            self._set_disconnected()
            # Keep the ping timer running so we detect when DLC comes back

    # -------------------------------------------------------------------------
    # Methods called by DLA to send data to DLC
    # -------------------------------------------------------------------------

    def notifyConnectionStatus(self, status):
        self.log_vtt(f"[BRIDGE] Connection status: {status}")
        self.connectionStatusReady.emit(status)

    def sendRollResult(self, roll_result_data):
        try:
            data_json = json.dumps(roll_result_data)
            self.log_vtt(f"[BRIDGE] Sending roll result: {roll_result_data.get('id', 'unknown')}")
            self.rollResultReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending roll result: {str(e)}")

    def sendRollCancelled(self, request_id, reason="User cancelled"):
        data = {"type": "rollCancelled", "id": request_id, "reason": reason}
        try:
            self.log_vtt(f"[BRIDGE] Sending roll cancelled: {request_id}")
            from state import app_state
            app_state.camera_stream_armed = False
            self.rollCancelledReady.emit(json.dumps(data))
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending roll cancelled: {str(e)}")

    def sendDiceResult(self, dice_result_data):
        try:
            data_json = json.dumps(dice_result_data)
            self.log_vtt(f"[BRIDGE] Sending dice result: {dice_result_data.get('id', 'unknown')}")
            from state import app_state
            app_state.camera_stream_armed = False
            self.diceResultReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending dice result: {str(e)}")

    def sendRollComplete(self, roll_data):
        try:
            data_json = json.dumps(roll_data)
            self.log_vtt(f"[BRIDGE] Sending roll complete: {roll_data.get('id', 'unknown')}")
            self.rollCompleteReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending roll complete: {str(e)}")

    def sendDiceTrayRoll(self, dice_tray_data):
        try:
            data_json = json.dumps(dice_tray_data)
            self.log_vtt(f"[BRIDGE] Sending dice tray roll: {dice_tray_data.get('id', 'unknown')}")
            self.diceTrayRollReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending dice tray roll: {str(e)}")

    def sendPlayerModesUpdate(self, player_modes_data):
        try:
            data_json = json.dumps(player_modes_data)
            self.log_vtt("[BRIDGE] Sending player modes update to DLC")
            self.playerModesUpdateReady.emit(data_json)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending player modes update: {str(e)}")

    def sendCameraFrame(self, frame_b64: str):
        try:
            self.cameraFrameReady.emit(frame_b64)
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending camera frame: {str(e)}")

    def sendCameraStreamEnd(self):
        try:
            self.cameraStreamEndReady.emit()
        except Exception as e:
            self.log_vtt(f"[BRIDGE] ERROR sending camera stream end: {str(e)}")
