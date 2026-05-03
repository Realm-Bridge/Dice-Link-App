"""FastAPI application setup for Dice Link"""

import json
import asyncio
import base64 as base64_module
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription

from state import app_state
from core.websocket_handler import broadcast_to_ui
from core.camera import camera_manager
from config import APP_NAME, APP_VERSION, DICE_RANGES, DEFAULT_CAMERA_INDEX, CAMERA_FPS
from debug import log_server, log_flicker
from bridge_state import send_dice_result_to_foundry, send_dice_tray_roll_to_foundry

# Get the base directory (now app.py is at the root of dice-link/)
BASE_DIR = Path(__file__).resolve().parent

# Create FastAPI app
app = FastAPI(title=APP_NAME, version=APP_VERSION)

# Add CORS middleware to allow requests from any origin (like the working test)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/startup")
async def startup(request: Request):
    """Serve the startup/login dialog"""
    return templates.TemplateResponse(
        request=request,
        name="startup.html",
        context={
            "app_name": APP_NAME,
            "app_version": APP_VERSION
        }
    )


@app.get("/api/dice-ranges")
async def get_dice_ranges():
    """Get valid dice value ranges"""
    return JSONResponse(DICE_RANGES)


# ============== Camera Endpoints ==============

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


@app.get("/api/camera/tray-region")
async def get_tray_region():
    """Return the stored tray polygon"""
    return JSONResponse({"points": camera_manager.tray_polygon})


@app.websocket("/ws/camera")
async def websocket_camera(websocket: WebSocket):
    """Binary WebSocket streaming raw RGBA frames for USB camera display"""
    await websocket.accept()
    frame_interval = 1.0 / CAMERA_FPS
    try:
        while True:
            if camera_manager.is_capturing:
                raw = camera_manager.get_raw_rgba_bytes(max_height=720)
                if raw:
                    await websocket.send_bytes(raw)
            await asyncio.sleep(frame_interval)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


dlc_frame_task = None

# ============== Phone Camera WebRTC ==============

phone_peer_connections: set = set()


async def _feed_camera_manager(track):
    """Decode phone video frames into camera_manager for motion detection and processing."""
    frame_count = 0
    try:
        while True:
            frame = await track.recv()
            img = frame.to_ndarray(format='bgr24')
            camera_manager.receive_phone_frame(img)
            frame_count += 1
            if frame_count == 1 or frame_count % 30 == 0:
                log_server(f"Phone camera: {frame_count} frames received, size={img.shape[1]}x{img.shape[0]}")
    except Exception as e:
        log_server(f"Phone camera feed stopped after {frame_count} frames: {type(e).__name__}: {e}")


@app.post("/api/phone-camera/offer")
async def phone_camera_offer(request: Request):
    """Accept a WebRTC SDP offer from the phone, return the answer."""
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    phone_peer_connections.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_server(f"Phone camera connection state: {pc.connectionState}")
        if pc.connectionState == "connected":
            await broadcast_to_ui({"type": "phone_camera_connected"})
        elif pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            phone_peer_connections.discard(pc)
            camera_manager.stop_capture()
            await broadcast_to_ui({"type": "phone_camera_disconnected"})

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            if camera_manager.is_capturing:
                camera_manager.stop_capture()
            camera_manager.select_camera(-1)
            camera_manager.start_capture()
            asyncio.ensure_future(_feed_camera_manager(track))

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    gather_done = asyncio.Event()

    @pc.on("icegatheringstatechange")
    def on_ice_gathering():
        if pc.iceGatheringState == "complete":
            gather_done.set()

    if pc.iceGatheringState == "complete":
        gather_done.set()

    try:
        await asyncio.wait_for(gather_done.wait(), timeout=10.0)
    except asyncio.TimeoutError:
        log_server("Phone camera ICE gathering timed out — returning partial SDP")

    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })



@app.get("/phone-camera")
async def phone_camera_page():
    """Phone camera page — scan QR code on phone, streams video to DLA via WebRTC over HTTPS."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Dice Link — Phone Camera</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: sans-serif; text-align: center; padding: 24px; background: #1a1a2e; color: #e0e0e0; }
        h1 { color: #c9a84c; margin-bottom: 4px; }
        h2 { color: #888; font-weight: normal; font-size: 16px; margin-bottom: 20px; }
        .status { margin: 0 auto 16px; padding: 14px 16px; border-radius: 8px; font-size: 16px; max-width: 420px; line-height: 1.4; }
        .waiting    { background: #2a2a4e; }
        .connecting { background: #7a3f00; }
        .success    { background: #1b4d20; }
        .error      { background: #6b1010; }
        video { width: 100%; max-width: 420px; border-radius: 8px; border: 2px solid #c9a84c; display: block; margin: 0 auto; }
        .reconnect-btn { margin-top: 16px; padding: 10px 28px; background: #c9a84c; color: #1a1a2e; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Dice Link</h1>
    <h2>Phone Camera</h2>
    <div id="status" class="status waiting">Requesting camera access…</div>
    <video id="video" autoplay playsinline muted></video>
    <script>
        async function connect() {
            const status = document.getElementById('status');
            const video  = document.getElementById('video');
            const existingBtn = document.getElementById('reconnect-btn');
            if (existingBtn) existingBtn.remove();
            try {
                status.className = 'status waiting';
                status.textContent = 'Requesting camera access…';
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment', width: { ideal: 3840 }, height: { ideal: 2160 } },
                    audio: false
                });
                video.srcObject = stream;
                status.className = 'status connecting';
                status.textContent = 'Connecting to Dice Link…';
                const pc = new RTCPeerConnection({ iceServers: [] });
                stream.getTracks().forEach(track => pc.addTrack(track, stream));
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                await new Promise(resolve => {
                    if (pc.iceGatheringState === 'complete') { resolve(); }
                    else {
                        pc.addEventListener('icegatheringstatechange', function check() {
                            if (pc.iceGatheringState === 'complete') {
                                pc.removeEventListener('icegatheringstatechange', check);
                                resolve();
                            }
                        });
                        setTimeout(resolve, 8000);
                    }
                });
                const response = await fetch('/api/phone-camera/offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type })
                });
                const answer = await response.json();
                await pc.setRemoteDescription(new RTCSessionDescription(answer));
                pc.addEventListener('connectionstatechange', function () {
                    if (pc.connectionState === 'connected') {
                        status.className = 'status success';
                        status.textContent = '✓ Connected — keep this page open while rolling';
                    } else if (['failed','disconnected','closed'].includes(pc.connectionState)) {
                        status.className = 'status error';
                        status.textContent = '✗ Connection lost';
                        showReconnect();
                    }
                });
            } catch (err) {
                status.className = 'status error';
                status.textContent = '✗ ' + err.name + ': ' + err.message;
                showReconnect();
            }
        }
        function showReconnect() {
            if (document.getElementById('reconnect-btn')) return;
            const btn = document.createElement('button');
            btn.id = 'reconnect-btn';
            btn.className = 'reconnect-btn';
            btn.textContent = 'Reconnect';
            btn.onclick = connect;
            document.body.appendChild(btn);
        }
        connect();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/phone-camera/qr")
async def phone_camera_qr():
    """Return QR code SVG — phone scans this to open the camera page over HTTPS."""
    import socket
    import io
    import qrcode
    import qrcode.image.svg
    from config import PHONE_CAMERA_PORT

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    ip_dashed = local_ip.replace(".", "-")
    phone_url = f"https://{ip_dashed}.my.local-ip.co:{PHONE_CAMERA_PORT}/phone-camera"

    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(phone_url, image_factory=factory)
    stream = io.BytesIO()
    img.save(stream)
    return Response(content=stream.getvalue(), media_type="image/svg+xml")


async def dlc_camera_stream_loop():
    """Send processed frames to DLC via bridge when motion is detected during an armed roll."""
    from bridge_state import send_camera_frame_to_dlc, send_camera_stream_end_to_dlc
    frame_interval = 1.0 / CAMERA_FPS
    was_motion = False

    while camera_manager.is_capturing:
        is_motion = camera_manager.is_motion

        # Only start streaming when a diceRequest has armed the camera
        if is_motion and app_state.camera_stream_armed:
            frame = camera_manager.get_processed_frame()
            if frame:
                frame_b64 = base64_module.b64encode(frame).decode('utf-8')
                send_camera_frame_to_dlc(frame_b64)
            was_motion = True
        elif was_motion and not is_motion:
            send_camera_stream_end_to_dlc()
            was_motion = False
            app_state.camera_stream_armed = False  # Disarm after roll completes

        await asyncio.sleep(frame_interval)


@app.post("/api/camera/start")
async def start_camera():
    """Start camera capture"""
    global dlc_frame_task
    success = camera_manager.start_capture(fps=CAMERA_FPS)
    if success and (dlc_frame_task is None or dlc_frame_task.done()):
        dlc_frame_task = asyncio.create_task(dlc_camera_stream_loop())
    return JSONResponse({
        "success": success,
        "fps": CAMERA_FPS
    })


@app.post("/api/camera/stop")
async def stop_camera():
    """Stop camera capture"""
    global dlc_frame_task
    if dlc_frame_task:
        dlc_frame_task.cancel()
        try:
            await dlc_frame_task
        except asyncio.CancelledError:
            pass
        dlc_frame_task = None
    camera_manager.stop_capture()
    return JSONResponse({"success": True})


@app.post("/api/camera/tray-region")
async def set_tray_region(request: Request):
    """Save the tray polygon region"""
    data = await request.json()
    points = data.get("points", [])
    success = camera_manager.set_tray_region(points)
    return JSONResponse({"success": success})


@app.get("/api/camera/motion")
async def camera_motion():
    """Get current motion detection state"""
    return JSONResponse({"motion": camera_manager.is_motion})


@app.post("/api/camera/calibrate")
async def calibrate_camera():
    """Capture current frame as background baseline"""
    success = camera_manager.calibrate()
    return JSONResponse({
        "success": success,
        "isCalibrated": camera_manager.is_calibrated
    })



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
    
    if msg_type == "reportFlicker":
        log_flicker()
        return

    if msg_type == "debug":
        # Debug messages from JavaScript - print to command prompt
        log_server(f"[JS] {message.get('message', '')}")
        return
    
    if msg_type == "diceTrayRoll":
        # Dice tray roll from UI - forward to DLC via QWebChannel bridge
        formula = message.get("formula", "")
        flavor = message.get("flavor", "Manual Dice Roll")
        log_server(f"Received diceTrayRoll from UI: formula={formula}, flavor={flavor}")
        
        success = send_dice_tray_roll_to_foundry(formula, flavor)
        
        await broadcast_to_ui({
            "type": "diceTrayRollAck",
            "success": success,
            "formula": formula
        })
        return
    
    if msg_type == "diceResult":
        log_server(f"Received diceResult from UI: {message}")
        original_roll_id = message.get("originalRollId")
        results = message.get("results", [])

        result_data = {
            "type": "diceResult",
            "id": original_roll_id,
            "results": results
        }
        bridge_success = send_dice_result_to_foundry(result_data)
        if bridge_success:
            log_server(f"Forwarded diceResult to Foundry via bridge")
        return
    
    if msg_type == "buttonSelect":
        log_server(f"Received buttonSelect from UI: {message}")
        roll_id = message.get("rollId")
        button = message.get("button")
        config_changes = message.get("configChanges", {})

        from bridge_state import send_button_select_to_dlc
        bridge_success = send_button_select_to_dlc({
            "type": "buttonSelect",
            "rollId": roll_id,
            "button": button,
            "configChanges": config_changes
        })
        if bridge_success:
            log_server(f"Forwarded buttonSelect to DLC via bridge: {button}")

        await broadcast_to_ui({
            "type": "buttonSelectAck",
            "success": bridge_success,
            "rollId": roll_id
        })
        return
    
    elif msg_type == "cancelRoll":
        roll_id = message.get("rollId")
        await broadcast_to_ui({
            "type": "cancelRollAck",
            "success": True,
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


