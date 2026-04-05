"""FastAPI application setup for Dice Link"""

import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from .state import app_state
from .websocket_handler import (
    handle_dlc_message,
    handle_dlc_disconnect,
    broadcast_to_ui,
    send_roll_result,
    send_roll_cancelled
)
from config import APP_NAME, APP_VERSION, DICE_RANGES

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Create FastAPI app
app = FastAPI(title=APP_NAME, version=APP_VERSION)

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


async def handle_ui_message(message: dict):
    """Handle messages from browser UI"""
    msg_type = message.get("type")
    
    if msg_type == "submitResult":
        # User submitted dice results
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
