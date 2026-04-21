"""FastAPI application setup for Dice Link"""

import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription

from state import app_state
from core.websocket_handler import (
    handle_dlc_message,
    handle_dlc_disconnect,
    broadcast_to_ui,
    send_roll_result,
    send_roll_cancelled,
    send_button_select,
    send_dice_result,
    send_dice_tray_roll,
    get_webrtc_connection_status,
    log_handshake_step
)
from core.camera import camera_manager
from config import APP_NAME, APP_VERSION, DICE_RANGES, DEFAULT_CAMERA_INDEX, CAMERA_FPS, CONNECTION_METHOD
from debug import log_dlc_connection, log_dlc_accepted, log_dlc_message, log_dlc_response, log_dlc_disconnect, log_server

# Get the base directory (now app.py is at the root of dice-link/)
BASE_DIR = Path(__file__).resolve().parent

# Create FastAPI app
app = FastAPI(title=APP_NAME, version=APP_VERSION)

# Add CORS middleware to allow requests from localhost test page
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8765", "http://127.0.0.1:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Setup templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
async def index(request: Request):
    """Serve the main UI"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": APP_NAME,
            "app_version": APP_VERSION
        }
    )


@app.get("/test-webrtc")
async def test_webrtc_page():
    """Simple HTML page for testing WebRTC handshake manually"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dice Link - WebRTC Test</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #ffffff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: #0f3460;
                border: 2px solid #e94560;
                border-radius: 12px;
                padding: 40px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 10px 40px rgba(233, 69, 96, 0.2);
            }
            
            h1 {
                text-align: center;
                margin-bottom: 30px;
                color: #e94560;
                font-size: 28px;
            }
            
            .step {
                margin-bottom: 30px;
            }
            
            .step-number {
                display: inline-block;
                background: #e94560;
                color: #0f3460;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                text-align: center;
                line-height: 32px;
                font-weight: bold;
                margin-right: 10px;
            }
            
            .step-title {
                display: inline;
                font-weight: 600;
                font-size: 16px;
            }
            
            label {
                display: block;
                margin-top: 15px;
                margin-bottom: 8px;
                font-weight: 500;
                font-size: 14px;
                color: #e0e0e0;
            }
            
            textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #533483;
                border-radius: 6px;
                background: #1a1a2e;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                resize: vertical;
                min-height: 100px;
            }
            
            textarea:focus {
                outline: none;
                border-color: #e94560;
                box-shadow: 0 0 10px rgba(233, 69, 96, 0.3);
            }
            
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                flex-wrap: wrap;
            }
            
            button {
                flex: 1;
                min-width: 120px;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .btn-send {
                background: #e94560;
                color: #0f3460;
            }
            
            .btn-send:hover {
                background: #ff5a7e;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(233, 69, 96, 0.4);
            }
            
            .btn-copy {
                background: #533483;
                color: #ffffff;
            }
            
            .btn-copy:hover {
                background: #6b44a6;
                transform: translateY(-2px);
            }
            
            .btn-copy:disabled {
                background: #333;
                cursor: not-allowed;
                opacity: 0.5;
            }
            
            .status {
                margin-top: 15px;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                text-align: center;
                display: none;
            }
            
            .status.show {
                display: block;
            }
            
            .status.success {
                background: rgba(46, 204, 113, 0.2);
                color: #2ecc71;
                border: 1px solid #2ecc71;
            }
            
            .status.error {
                background: rgba(233, 69, 96, 0.2);
                color: #ff6b7a;
                border: 1px solid #ff6b7a;
            }
            
            .status.loading {
                background: rgba(83, 52, 131, 0.2);
                color: #b19cd9;
                border: 1px solid #b19cd9;
            }
            
            .info {
                background: rgba(83, 52, 131, 0.3);
                border-left: 4px solid #e94560;
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-size: 13px;
                line-height: 1.6;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎲 Dice Link WebRTC Test</h1>
            
            <div class="info">
                <strong>Instructions:</strong><br>
                1. Copy the offer from DLC<br>
                2. Paste it below<br>
                3. Click "Send to DLA"<br>
                4. Copy the answer and paste it back into DLC
            </div>
            
            <div class="step">
                <span class="step-number">1</span>
                <span class="step-title">Paste the Offer from DLC</span>
                <label for="offer">Offer (from DLC):</label>
                <textarea id="offer" placeholder="Paste the connection offer here..."></textarea>
            </div>
            
            <div class="button-group">
                <button class="btn-send" onclick="sendOffer()">Send to DLA</button>
            </div>
            
            <div id="status" class="status"></div>
            
            <div class="step" style="margin-top: 30px;">
                <span class="step-number">2</span>
                <span class="step-title">Copy the Answer from DLA</span>
                <label for="answer">Answer (from DLA):</label>
                <textarea id="answer" placeholder="The answer will appear here..." readonly></textarea>
            </div>
            
            <div class="button-group">
                <button class="btn-copy" id="copyBtn" onclick="copyAnswer()" disabled>Copy Answer</button>
            </div>
        </div>
        
        <script>
            async function sendOffer() {
                const offer = document.getElementById('offer').value;
                const status = document.getElementById('status');
                const answerField = document.getElementById('answer');
                
                if (!offer.trim()) {
                    showStatus('Please paste an offer first', 'error');
                    return;
                }
                
                showStatus('Sending offer to DLA...', 'loading');
                
                try {
                    const response = await fetch('http://localhost:8765/api/receive-offer', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ offer: offer })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        showStatus('Error: ' + (error.error || 'Failed to get answer'), 'error');
                        return;
                    }
                    
                    const data = await response.json();
                    answerField.value = data.answer;
                    document.getElementById('copyBtn').disabled = false;
                    showStatus('Success! Answer received. Click "Copy Answer" to copy it.', 'success');
                } catch (error) {
                    showStatus('Error: ' + error.message, 'error');
                }
            }
            
            function copyAnswer() {
                const answerField = document.getElementById('answer');
                answerField.select();
                document.execCommand('copy');
                showStatus('Answer copied to clipboard!', 'success');
                setTimeout(() => showStatus('', 'success'), 3000);
            }
            
            function showStatus(message, type) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = 'status show ' + type;
            }
            
            // Allow Enter key to send
            document.getElementById('offer').addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'Enter') {
                    sendOffer();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

async def get_status():
    """Get current application status"""
    return JSONResponse(app_state.get_status())


@app.get("/api/dice-ranges")
async def get_dice_ranges():
    """Get valid dice value ranges"""
    return JSONResponse(DICE_RANGES)


@app.get("/api/external-ip")
async def get_external_ip_endpoint():
    """Get external IP for DLC configuration"""
    from upnp import get_external_ip
    external_ip = get_external_ip()
    return JSONResponse({
        "externalIp": external_ip,
        "port": 8765,
        "wsUrl": f"ws://{external_ip}:8765/ws/dlc" if external_ip else None
    })


# ============== WebRTC Signaling Endpoints ==============

@app.post("/api/receive-offer")
async def receive_webrtc_offer(request: Request):
    """
    Browser-as-offerer WebRTC handshake endpoint.
    DLC generates offer locally, sends to DLA here, DLA generates answer.
    
    Request body: {"offer": "<SDP offer string>"}
    Response: {"answer": "<SDP answer string>", "status": "success"}
    """
    try:
        log_handshake_step(1, "Receive Offer", "HTTP POST received from browser")
        
        data = await request.json()
        browser_offer_sdp = data.get("offer")
        
        if not browser_offer_sdp:
            log_handshake_step(1.5, "Validation Failed", "No offer provided in request body")
            return JSONResponse(
                {"error": "No offer provided", "status": "error"},
                status_code=400
            )
        
        log_handshake_step(2, "Parse Offer", f"Received {len(browser_offer_sdp)} bytes of SDP from browser")
        
        # Create new peer connection for this handshake
        pc = RTCPeerConnection()
        log_handshake_step(3, "Create Peer Connection", "RTCPeerConnection initialized")
        
        # Create data channel for bidirectional messaging
        # Browser will use this channel to send messages
        data_channel = pc.createDataChannel("dice-link")
        log_handshake_step(4, "Create Data Channel", "Data channel 'dice-link' created")
        
        # Set up data channel handlers
        @data_channel.on("message")
        def on_message(message):
            log_server(f"WebRTC Message: {message}")
        
        @data_channel.on("open")
        def on_open():
            log_handshake_step(7, "Data Channel Open", "Browser data channel is ready for messaging")
        
        @data_channel.on("close")
        def on_close():
            log_handshake_step(8, "Data Channel Close", "Browser data channel closed")
        
        # Set remote description (browser's offer)
        try:
            log_handshake_step(5, "Set Remote Description", "Parsing browser SDP offer")
            browser_offer = RTCSessionDescription(
                sdp=browser_offer_sdp,
                type="offer"
            )
            await pc.setRemoteDescription(browser_offer)
            log_handshake_step(5.5, "Remote Description Set", "Browser offer successfully set as remote description")
        except Exception as e:
            log_handshake_step(5.9, "Remote Description Failed", f"Error: {e}")
            return JSONResponse(
                {"error": f"Failed to parse browser offer: {str(e)}", "status": "error"},
                status_code=400
            )
        
        # Create answer
        try:
            log_handshake_step(6, "Create Answer", "Generating DLA answer to browser offer")
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            log_handshake_step(6.5, "Answer Created", "Answer generated and set as local description")
        except Exception as e:
            log_handshake_step(6.9, "Answer Failed", f"Error: {e}")
            return JSONResponse(
                {"error": f"Failed to create answer: {str(e)}", "status": "error"},
                status_code=500
            )
        
        # Get answer SDP
        answer_sdp = pc.localDescription.sdp
        log_handshake_step(6.7, "Serialize Answer", f"Answer serialized ({len(answer_sdp)} bytes)")
        
        # Store peer connection and data channel in state
        await app_state.set_webrtc_peer_connection(pc, data_channel)
        log_handshake_step(6.8, "Store Connection", "Peer connection stored in application state")
        
        # Notify UI that WebRTC connection is being established
        await broadcast_to_ui({
            "type": "webrtcStatus",
            "event": "offering",
            "message": "WebRTC handshake in progress..."
        })
        log_handshake_step(6.9, "UI Notification", "Browser UI notified of handshake progress")
        
        log_handshake_step(9, "Send Answer", f"Returning answer to browser ({len(answer_sdp)} bytes)")
        
        return JSONResponse({
            "answer": answer_sdp,
            "status": "success"
        })
    
    except Exception as e:
        log_handshake_step(99, "Unhandled Error", f"Exception: {e}")
        return JSONResponse(
            {"error": str(e), "status": "error"},
            status_code=500
        )


@app.get("/api/webrtc-status")
async def get_webrtc_status():
    """Get current WebRTC connection status"""
    status = get_webrtc_connection_status()
    return JSONResponse(status)


# ============== WebRTC Testing Endpoints (Phase 2) ==============

@app.post("/api/test-webrtc")
async def test_webrtc_connection(request: Request):
    """
    Test endpoint to verify WebRTC connection is established.
    DLC sends a test message, DLA echoes it back.
    
    Request body: {"message": "test message"}
    Response: {"success": true, "echo": "test message"}
    """
    try:
        data = await request.json()
        test_message = data.get("message", "ping")
        
        log_server(f"test_webrtc_connection: Received test message: {test_message}")
        
        # Verify we have an active data channel
        if not app_state.webrtc_data_channel or app_state.webrtc_data_channel.readyState != "open":
            log_server("test_webrtc_connection: Data channel not open")
            return JSONResponse({
                "success": False,
                "error": "WebRTC data channel not open",
                "dataChannelState": getattr(app_state.webrtc_data_channel, "readyState", "closed") if app_state.webrtc_data_channel else "none"
            }, status_code=503)
        
        # Send test message back through data channel
        # This uses HTTP for response, but we also send via WebRTC to test bidirectional
        test_response = {
            "type": "test",
            "echo": test_message,
            "timestamp": int(time.time() * 1000)
        }
        
        try:
            app_state.webrtc_data_channel.send(json.dumps(test_response))
            log_server(f"test_webrtc_connection: Echo sent via WebRTC: {test_message}")
        except Exception as e:
            log_server(f"test_webrtc_connection: Error sending via WebRTC: {e}")
        
        return JSONResponse({
            "success": True,
            "echo": test_message,
            "message": "Test message received and echoed"
        })
    
    except Exception as e:
        log_server(f"test_webrtc_connection: Error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/disconnect-webrtc")
async def disconnect_webrtc():
    """
    Cleanly close the WebRTC connection.
    Used for testing and resetting connection state.
    """
    try:
        log_server("disconnect_webrtc: Closing WebRTC connection")
        
        if app_state.webrtc_data_channel:
            try:
                app_state.webrtc_data_channel.close()
                log_server("disconnect_webrtc: Data channel closed")
            except Exception as e:
                log_server(f"disconnect_webrtc: Error closing data channel: {e}")
        
        if app_state.webrtc_peer_connection:
            try:
                await app_state.webrtc_peer_connection.close()
                log_server("disconnect_webrtc: Peer connection closed")
            except Exception as e:
                log_server(f"disconnect_webrtc: Error closing peer connection: {e}")
        
        await app_state.close_webrtc_connection()
        
        # Notify UI
        await broadcast_to_ui({
            "type": "webrtcStatus",
            "event": "disconnected",
            "message": "WebRTC connection closed"
        })
        
        return JSONResponse({
            "success": True,
            "message": "WebRTC connection closed"
        })
    
    except Exception as e:
        log_server(f"disconnect_webrtc: Unhandled error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# ============== Camera Endpoints (Phase 3) ==============

@app.get("/api/cameras")
async def list_cameras():
    """Get list of available cameras"""
    cameras = camera_manager.list_cameras()
    return JSONResponse({
        "cameras": cameras,
        "selectedIndex": camera_manager.camera_index
    })


@app.post("/api/camera/select")
async def select_camera(request: Request):
    """Select a camera by index"""
    data = await request.json()
    index = data.get("index", 0)
    
    success = camera_manager.select_camera(index)
    return JSONResponse({
        "success": success,
        "selectedIndex": camera_manager.camera_index
    })


@app.get("/api/camera/preview")
async def camera_preview():
    """Get a single frame preview from the selected camera"""
    frame = camera_manager.capture_single_frame()
    if frame:
        return JSONResponse({
            "success": True,
            "frame": frame
        })
    return JSONResponse({
        "success": False,
        "error": "Failed to capture frame"
    })


@app.post("/api/camera/start")
async def start_camera():
    """Start camera capture"""
    success = camera_manager.start_capture(fps=CAMERA_FPS)
    return JSONResponse({
        "success": success,
        "fps": CAMERA_FPS
    })


@app.post("/api/camera/stop")
async def stop_camera():
    """Stop camera capture"""
    camera_manager.stop_capture()
    return JSONResponse({"success": True})


@app.websocket("/ws/ui")
async def websocket_ui(websocket: WebSocket):
    """WebSocket endpoint for browser UI connections"""
    await websocket.accept()
    app_state.add_ui_websocket(websocket)
    
    # Send current status on connect
    await websocket.send_text(json.dumps({
        "type": "status",
        "data": app_state.get_status()
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_ui_message(message)
    except WebSocketDisconnect:
        app_state.remove_ui_websocket(websocket)
    except Exception as e:
        log_server(f"UI WebSocket error: {e}")
        app_state.remove_ui_websocket(websocket)


# Camera streaming state
camera_stream_task = None
camera_stream_active = False


async def camera_stream_loop():
    """Background task to stream camera frames to UI"""
    global camera_stream_active
    
    frame_interval = 1.0 / CAMERA_FPS
    
    while camera_stream_active and camera_manager.is_capturing:
        frame = camera_manager.get_frame()
        if frame:
            await broadcast_to_ui({
                "type": "cameraFrame",
                "frame": frame
            })
        await asyncio.sleep(frame_interval)


async def start_camera_stream():
    """Start streaming camera frames to UI"""
    global camera_stream_task, camera_stream_active
    
    if camera_stream_active:
        return True
    
    # Start camera capture
    success = camera_manager.start_capture(fps=CAMERA_FPS)
    if not success:
        return False
    
    camera_stream_active = True
    camera_stream_task = asyncio.create_task(camera_stream_loop())
    return True


async def stop_camera_stream():
    """Stop streaming camera frames"""
    global camera_stream_task, camera_stream_active
    
    camera_stream_active = False
    
    if camera_stream_task:
        camera_stream_task.cancel()
        try:
            await camera_stream_task
        except asyncio.CancelledError:
            pass
        camera_stream_task = None
    
    camera_manager.stop_capture()


async def handle_ui_message(message: dict):
    """Handle messages from browser UI"""
    msg_type = message.get("type")
    
    if msg_type == "debug":
        # Debug messages from JavaScript - print to command prompt
        log_server(f"[JS] {message.get('message', '')}")
        return
    
    if msg_type == "diceTrayRoll":
        # Dice tray roll from UI - forward to DLC for evaluation
        formula = message.get("formula", "")
        flavor = message.get("flavor", "Manual Dice Roll")
        log_server(f"Received diceTrayRoll from UI: formula={formula}, flavor={flavor}")
        
        success = await send_dice_tray_roll(formula, flavor)
        
        await broadcast_to_ui({
            "type": "diceTrayRollAck",
            "success": success,
            "formula": formula
        })
        return
    
    if msg_type == "diceResult":
        # User submitted dice results - forward to DLC
        log_server(f"Received diceResult from UI: {message}")
        original_roll_id = message.get("originalRollId")
        results = message.get("results", [])
        
        success = await send_dice_result(original_roll_id, results)
        log_server(f"Forwarded diceResult to DLC, success={success}")
        
        await broadcast_to_ui({
            "type": "diceResultAck",
            "success": success,
            "rollId": original_roll_id
        })
        return
    
    if msg_type == "buttonSelect":
        # Phase A: User selected a button (Advantage/Normal/Disadvantage)
        roll_id = message.get("rollId")
        button = message.get("button")
        config_changes = message.get("configChanges", {})
        
        success = await send_button_select(roll_id, button, config_changes)
        
        await broadcast_to_ui({
            "type": "buttonSelectAck",
            "success": success,
            "rollId": roll_id
        })
    
    elif msg_type == "submitDiceResult":
        # Phase B: User submitted dice results after diceRequest
        log_server(f"Received submitDiceResult from UI: {message}")
        original_roll_id = message.get("originalRollId")
        results = message.get("results", [])
        
        log_server(f"Calling send_dice_result with originalRollId={original_roll_id}, results={results}")
        success = await send_dice_result(original_roll_id, results)
        log_server(f"send_dice_result returned: {success}")
        
        await broadcast_to_ui({
            "type": "submitResultAck",
            "success": success,
            "rollId": original_roll_id
        })
    
    elif msg_type == "submitResult":
        # Legacy: User submitted dice results (single-phase, kept for compatibility)
        roll_id = message.get("rollId")
        button_clicked = message.get("buttonClicked")
        config_changes = message.get("configChanges", {})
        results = message.get("results", [])
        
        success = await send_roll_result(roll_id, button_clicked, config_changes, results)
        
        await broadcast_to_ui({
            "type": "submitResultAck",
            "success": success,
            "rollId": roll_id
        })
    
    elif msg_type == "cancelRoll":
        # User cancelled the roll
        roll_id = message.get("rollId")
        reason = message.get("reason", "User cancelled")
        
        success = await send_roll_cancelled(roll_id, reason)
        
        await broadcast_to_ui({
            "type": "cancelRollAck",
            "success": success,
            "rollId": roll_id
        })
    
    elif msg_type == "startCameraStream":
        # Start camera streaming
        success = await start_camera_stream()
        await broadcast_to_ui({
            "type": "cameraStreamStatus",
            "active": success
        })
    
    elif msg_type == "stopCameraStream":
        # Stop camera streaming
        await stop_camera_stream()
        await broadcast_to_ui({
            "type": "cameraStreamStatus",
            "active": False
        })


@app.websocket("/ws/dlc")
async def websocket_dlc(websocket: WebSocket):
    """
    WebSocket endpoint for DLC connections.
    DISABLED when CONNECTION_METHOD = "webrtc" - kept as fallback only.
    To re-enable: set CONNECTION_METHOD = "websocket" in config.py
    """
    if CONNECTION_METHOD == "webrtc":
        log_server("ws/dlc: Connection attempt rejected - WebSocket is disabled (CONNECTION_METHOD=webrtc)")
        await websocket.close(code=1013, reason="WebSocket disabled - use WebRTC connection method")
        return
    
    # Debug logging via centralized debug module
    client = websocket.client
    if client:
        log_dlc_connection(client.host, client.port, dict(websocket.headers))
    else:
        log_dlc_connection("unknown", 0, dict(websocket.headers))
    
    await websocket.accept()
    log_dlc_accepted()
    
    try:
        while True:
            data = await websocket.receive_text()
            log_dlc_message(data)
            message = json.loads(data)
            
            response = await handle_dlc_message(websocket, message)
            
            if response:
                log_dlc_response(json.dumps(response))
                await websocket.send_text(json.dumps(response))
    
    except WebSocketDisconnect:
        log_dlc_disconnect(clean=True)
        await handle_dlc_disconnect()
    except Exception as e:
        log_dlc_disconnect(clean=False, error=f"{type(e).__name__}: {e}")
        await handle_dlc_disconnect()
