"""FastAPI application setup for Dice Link"""

import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from state import app_state
from core.websocket_handler import (
    handle_dlc_message,
    handle_dlc_disconnect,
    broadcast_to_ui,
    send_roll_result,
    send_roll_cancelled,
    send_button_select,
    send_dice_result,
    send_dice_tray_roll
)
from core.camera import camera_manager
from config import APP_NAME, APP_VERSION, DICE_RANGES, DEFAULT_CAMERA_INDEX, CAMERA_FPS

# Get the base directory (now app.py is at the root of dice-link/)
BASE_DIR = Path(__file__).resolve().parent

# Create FastAPI app
app = FastAPI(title=APP_NAME, version=APP_VERSION)


# Custom middleware to handle Private Network Access preflight requests
class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle Chrome's Private Network Access (PNA) preflight requests.
    When a webpage loaded from a public IP tries to connect to localhost,
    Chrome sends a preflight request that requires specific headers in the response.
    """
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests for Private Network Access
        if request.method == "OPTIONS":
            # Check if this is a Private Network Access preflight
            if request.headers.get("Access-Control-Request-Private-Network") == "true":
                response = Response(status_code=204)
                response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Private-Network"] = "true"
                return response
        
        # Process the request normally
        response = await call_next(request)
        
        # Add Private Network Access headers to all responses
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        
        return response


# Add Private Network Access middleware (must be added before CORS)
app.add_middleware(PrivateNetworkAccessMiddleware)

# Add CORS middleware to allow cross-origin requests
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


@app.get("/api/status")
async def get_status():
    """Get current application status"""
    return JSONResponse(app_state.get_status())


@app.get("/api/dice-ranges")
async def get_dice_ranges():
    """Get valid dice value ranges"""
    return JSONResponse(DICE_RANGES)


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
        print(f"UI WebSocket error: {e}")
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
        print(f"[JS] {message.get('message', '')}")
        return
    
    if msg_type == "diceTrayRoll":
        # Dice tray roll from UI - forward to DLC for evaluation
        formula = message.get("formula", "")
        flavor = message.get("flavor", "Manual Dice Roll")
        print(f"[DLA] Received diceTrayRoll from UI: formula={formula}, flavor={flavor}")
        
        success = await send_dice_tray_roll(formula, flavor)
        
        await broadcast_to_ui({
            "type": "diceTrayRollAck",
            "success": success,
            "formula": formula
        })
        return
    
    if msg_type == "diceResult":
        # User submitted dice results - forward to DLC
        print(f"[DLA] Received diceResult from UI: {message}")
        original_roll_id = message.get("originalRollId")
        results = message.get("results", [])
        
        success = await send_dice_result(original_roll_id, results)
        print(f"[DLA] Forwarded diceResult to DLC, success={success}")
        
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
        print(f"[DLA] Received submitDiceResult from UI: {message}")
        original_roll_id = message.get("originalRollId")
        results = message.get("results", [])
        
        print(f"[DLA] Calling send_dice_result with originalRollId={original_roll_id}, results={results}")
        success = await send_dice_result(original_roll_id, results)
        print(f"[DLA] send_dice_result returned: {success}")
        
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
    """WebSocket endpoint for DLC connections"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            response = await handle_dlc_message(websocket, message)
            
            if response:
                await websocket.send_text(json.dumps(response))
    
    except WebSocketDisconnect:
        await handle_dlc_disconnect()
    except Exception as e:
        print(f"DLC WebSocket error: {e}")
        await handle_dlc_disconnect()
