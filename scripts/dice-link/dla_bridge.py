"""DLABridge - QWebChannel bridge for communication between DLA and DLC."""

import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from debug import log_vtt, log_connection_monitor


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
    connectionPingReady = pyqtSignal()  # Pings DLC to check if it's still responsive
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_vtt = log_vtt  # Store reference to logging function
        self.connection_check_timer = None
        self.pending_pong = False  # Flag to track if we're waiting for a pong
        self.log_vtt("[BRIDGE] DLABridge created")
    
    @pyqtSlot()
    def dlcModuleInitialized(self):
        """
        Called by JavaScript (DLC module) when it has loaded and initialized.
        DLC uses this to announce it's ready and establish the connection.
        """
        self.log_vtt("[BRIDGE] DLC module has initialized and announced it's ready")
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
    
    @pyqtSlot()
    def receiveConnectionPong(self):
        """
        Called by JavaScript (DLC module) in response to our connectionPing.
        Used to verify DLC is still responsive.
        """
        log_connection_monitor(f"Received pong from DLC - connection is active")
        self.pending_pong = False
    
    @pyqtSlot(str)
    def receiveRollRequest(self, data_json):
        """
        Called by JavaScript (DLC module) to send a roll request to DLA.
        
        Args:
            data_json: JSON string containing roll request data
        """
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
        """Start periodic ping checks (every 60 seconds)"""
        from PyQt6.QtCore import QTimer
        self.pending_pong = False  # Reset pending pong state from any previous connection
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.send_connection_ping)
        self.connection_check_timer.start(60000)  # 60 seconds
        self.log_vtt("[BRIDGE] Started connection monitoring (60 second ping interval)")
        log_connection_monitor("Started connection monitoring - pinging DLC every 60 seconds")
    
    def stop_connection_monitoring(self):
        """Stop the connection check timer"""
        if self.connection_check_timer:
            self.connection_check_timer.stop()
            self.log_vtt("[BRIDGE] Stopped connection monitoring")
            log_connection_monitor("Stopped connection monitoring")
    
    def send_connection_ping(self):
        """
        Send a ping to DLC and check if we get a pong back within 10 seconds.
        If no pong is received, consider the connection dead.
        """
        if self.pending_pong:
            # We already sent a ping and didn't get a pong back - connection is dead
            log_connection_monitor("TIMEOUT - No pong received from previous ping, connection is dead")
            self.log_vtt("[BRIDGE] Connection timeout - DLC did not respond to ping")
            self.notifyConnectionStatus("disconnected")
            from bridge_state import send_connection_status_to_ui
            send_connection_status_to_ui(connected=False)
            self.stop_connection_monitoring()
            return
        
        # Send ping to DLC
        log_connection_monitor("Sending ping to DLC, expecting pong within 10 seconds")
        self.pending_pong = True
        self.connectionPingReady.emit()
        
        # Set a 10-second timeout - if no pong arrives before the next check (60s away),
        # the next check will detect pending_pong is still True and disconnect
    
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
