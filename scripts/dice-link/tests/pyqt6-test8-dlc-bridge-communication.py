"""
Test DLABridge QWebChannel communication with simulated DLC module behavior.

This test verifies:
1. window.dlaInterface is available after page load
2. JavaScript can call Python methods (receiveRollRequest)
3. Python can emit signals back to JavaScript (rollResultReady)
4. Full round-trip communication works
5. All message types are handled correctly
"""

import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView

from main import VTTWebView


class DLCSimulator(QMainWindow):
    """Simulates DLC module behavior to test DLABridge communication"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DLA Bridge Communication Test - DLC Simulator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Setup UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status label
        self.status_label = QLabel("Ready. Click buttons to test communication.")
        layout.addWidget(self.status_label)
        
        # Test log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        # Buttons for testing
        self.test_button_1 = QPushButton("Test 1: Check window.dlaInterface exists")
        self.test_button_1.clicked.connect(self.test_interface_exists)
        layout.addWidget(self.test_button_1)
        
        self.test_button_2 = QPushButton("Test 2: Send Roll Request")
        self.test_button_2.clicked.connect(self.test_send_roll_request)
        layout.addWidget(self.test_button_2)
        
        self.test_button_3 = QPushButton("Test 3: Simulate DLC listening for results")
        self.test_button_3.clicked.connect(self.test_signal_listening)
        layout.addWidget(self.test_button_3)
        
        self.test_button_4 = QPushButton("Test 4: Send Dice Request")
        self.test_button_4.clicked.connect(self.test_send_dice_request)
        layout.addWidget(self.test_button_4)
        
        self.test_button_5 = QPushButton("Test 5: Send Player Modes Update")
        self.test_button_5.clicked.connect(self.test_send_player_modes)
        layout.addWidget(self.test_button_5)
        
        # Web view to load Foundry
        self.view = VTTWebView("http://83.105.151.227:30000")
        layout.addWidget(self.view)
        
        self.log_message("[TEST] Test harness created")
    
    def log_message(self, message):
        """Log message to the UI"""
        self.log.append(message)
        print(message)
    
    def test_interface_exists(self):
        """Test 1: Verify window.dlaInterface exists"""
        self.log_message("\n=== Test 1: Check window.dlaInterface ===")
        
        check_script = """
        (function() {
            var result = {
                hasDlaInterface: typeof window.dlaInterface !== 'undefined',
                hasReceiveRollRequest: typeof window.dlaInterface?.receiveRollRequest === 'function',
                hasRollResultSignal: typeof window.dlaInterface?.rollResultReady !== 'undefined',
                dlaInterfaceReady: window.dlaInterfaceReady || false
            };
            return JSON.stringify(result);
        })();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                self.log_message(f"[TEST 1] Result: {json.dumps(data, indent=2)}")
                if data['hasDlaInterface'] and data['hasReceiveRollRequest']:
                    self.log_message("[TEST 1] ✓ PASS: window.dlaInterface exists and is callable")
                else:
                    self.log_message("[TEST 1] ✗ FAIL: window.dlaInterface not properly exposed")
            except:
                self.log_message(f"[TEST 1] Error parsing result: {result}")
        
        self.view.page().runJavaScript(check_script, on_result)
    
    def test_send_roll_request(self):
        """Test 2: Send a roll request to DLA"""
        self.log_message("\n=== Test 2: Send Roll Request ===")
        
        # Create a sample roll request (matching DLC format)
        roll_request = {
            "type": "rollRequest",
            "id": "dlc-1234567890-2",
            "timestamp": int(time.time() * 1000),
            "player": {
                "id": "test-player-id",
                "name": "Test Player"
            },
            "roll": {
                "title": "Longsword Attack",
                "subtitle": "1d20 + 5",
                "formula": "1d20 + 5",
                "dice": [{"type": "d20", "count": 1}]
            },
            "config": {
                "fields": []
            },
            "buttons": [
                {"id": "advantage", "label": "Advantage"},
                {"id": "normal", "label": "Normal"},
                {"id": "disadvantage", "label": "Disadvantage"}
            ]
        }
        
        send_script = f"""
        (function() {{
            if (!window.dlaInterface) {{
                return JSON.stringify({{success: false, error: 'dlaInterface not available'}});
            }}
            
            try {{
                var rollData = {json.dumps(roll_request)};
                window.dlaInterface.receiveRollRequest(JSON.stringify(rollData));
                return JSON.stringify({{success: true, message: 'Roll request sent'}});
            }} catch (e) {{
                return JSON.stringify({{success: false, error: e.message}});
            }}
        }})();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                self.log_message(f"[TEST 2] Result: {json.dumps(data, indent=2)}")
                if data['success']:
                    self.log_message("[TEST 2] ✓ PASS: Roll request sent to Python")
                else:
                    self.log_message(f"[TEST 2] ✗ FAIL: {data.get('error', 'Unknown error')}")
            except:
                self.log_message(f"[TEST 2] Error parsing result: {result}")
        
        self.view.page().runJavaScript(send_script, on_result)
    
    def test_signal_listening(self):
        """Test 3: Simulate DLC listening for roll results"""
        self.log_message("\n=== Test 3: Listen for Roll Results ===")
        
        setup_listener_script = """
        (function() {
            if (!window.dlaInterface) {
                return JSON.stringify({success: false, error: 'dlaInterface not available'});
            }
            
            // DLC would set up listeners like this
            try {
                // Store a global reference for testing
                window.testResults = [];
                
                // Connect to rollResultReady signal
                if (window.dlaInterface.rollResultReady) {
                    window.dlaInterface.rollResultReady.connect(function(resultJson) {
                        console.log('[DLC] Received roll result: ' + resultJson);
                        window.testResults.push({
                            type: 'rollResult',
                            data: JSON.parse(resultJson)
                        });
                    });
                }
                
                // Connect to rollCancelled signal
                if (window.dlaInterface.rollCancelled) {
                    window.dlaInterface.rollCancelled.connect(function(cancelJson) {
                        console.log('[DLC] Received roll cancelled: ' + cancelJson);
                        window.testResults.push({
                            type: 'rollCancelled',
                            data: JSON.parse(cancelJson)
                        });
                    });
                }
                
                return JSON.stringify({
                    success: true,
                    message: 'Signal listeners registered'
                });
            } catch (e) {
                return JSON.stringify({success: false, error: e.message});
            }
        })();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                self.log_message(f"[TEST 3] Result: {json.dumps(data, indent=2)}")
                if data['success']:
                    self.log_message("[TEST 3] ✓ PASS: Signal listeners registered")
                    self.log_message("[TEST 3] Now simulating DLA sending a roll result...")
                    
                    # Schedule sending a result from Python side
                    QTimer.singleShot(1000, self.send_test_roll_result)
                else:
                    self.log_message(f"[TEST 3] ✗ FAIL: {data.get('error', 'Unknown error')}")
            except:
                self.log_message(f"[TEST 3] Error parsing result: {result}")
        
        self.view.page().runJavaScript(setup_listener_script, on_result)
    
    def send_test_roll_result(self):
        """Send a test roll result from Python (DLA side)"""
        self.log_message("[TEST 3] Sending roll result from Python to JavaScript...")
        
        roll_result = {
            "type": "rollResult",
            "id": "dlc-1234567890-2",
            "timestamp": int(time.time() * 1000),
            "button": "normal",
            "configChanges": {"rollMode": "gmroll"},
            "results": [{"type": "d20", "value": 17}]
        }
        
        # Send via the bridge
        if hasattr(self.view, 'dla_bridge'):
            self.view.dla_bridge.sendRollResult(roll_result)
            self.log_message("[TEST 3] Roll result emitted from Python")
            
            # Check if JavaScript received it
            QTimer.singleShot(500, self.check_received_results)
    
    def check_received_results(self):
        """Check if JavaScript received the results"""
        check_script = """
        (function() {
            return JSON.stringify({
                receivedResults: window.testResults || [],
                count: (window.testResults || []).length
            });
        })();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                self.log_message(f"[TEST 3] JavaScript received {data['count']} results")
                if data['count'] > 0:
                    self.log_message(f"[TEST 3] Results: {json.dumps(data['receivedResults'], indent=2)}")
                    self.log_message("[TEST 3] ✓ PASS: Round-trip communication successful!")
                else:
                    self.log_message("[TEST 3] ✗ FAIL: No results received in JavaScript")
            except:
                self.log_message(f"[TEST 3] Error checking results: {result}")
        
        self.view.page().runJavaScript(check_script, on_result)
    
    def test_send_dice_request(self):
        """Test 4: Send a dice request"""
        self.log_message("\n=== Test 4: Send Dice Request ===")
        
        dice_request = {
            "type": "diceRequest",
            "id": "dice-1234567890-1",
            "timestamp": int(time.time() * 1000),
            "dice": "4d6"
        }
        
        send_script = f"""
        (function() {{
            if (!window.dlaInterface) {{
                return JSON.stringify({{success: false, error: 'dlaInterface not available'}});
            }}
            
            try {{
                var diceData = {json.dumps(dice_request)};
                window.dlaInterface.receiveDiceRequest(JSON.stringify(diceData));
                return JSON.stringify({{success: true, message: 'Dice request sent'}});
            }} catch (e) {{
                return JSON.stringify({{success: false, error: e.message}});
            }}
        }})();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                if data['success']:
                    self.log_message("[TEST 4] ✓ PASS: Dice request sent to Python")
                else:
                    self.log_message(f"[TEST 4] ✗ FAIL: {data.get('error', 'Unknown error')}")
            except:
                self.log_message(f"[TEST 4] Error: {result}")
        
        self.view.page().runJavaScript(send_script, on_result)
    
    def test_send_player_modes(self):
        """Test 5: Send player modes update"""
        self.log_message("\n=== Test 5: Send Player Modes Update ===")
        
        modes_update = {
            "type": "playerModesUpdate",
            "timestamp": int(time.time() * 1000),
            "modes": ["Digital", "Manual"]
        }
        
        send_script = f"""
        (function() {{
            if (!window.dlaInterface) {{
                return JSON.stringify({{success: false, error: 'dlaInterface not available'}});
            }}
            
            try {{
                var modesData = {json.dumps(modes_update)};
                window.dlaInterface.receivePlayerModesUpdate(JSON.stringify(modesData));
                return JSON.stringify({{success: true, message: 'Player modes update sent'}});
            }} catch (e) {{
                return JSON.stringify({{success: false, error: e.message}});
            }}
        }})();
        """
        
        def on_result(result):
            try:
                data = json.loads(result)
                if data['success']:
                    self.log_message("[TEST 5] ✓ PASS: Player modes update sent to Python")
                else:
                    self.log_message(f"[TEST 5] ✗ FAIL: {data.get('error', 'Unknown error')}")
            except:
                self.log_message(f"[TEST 5] Error: {result}")
        
        self.view.page().runJavaScript(send_script, on_result)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    window = DLCSimulator()
    window.show()
    
    sys.exit(app.exec())
