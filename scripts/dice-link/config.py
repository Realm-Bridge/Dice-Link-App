"""Configuration settings for Dice Link"""

# Communication via QWebChannel — DLC runs inside DLA's embedded Foundry browser
CONNECTION_METHOD = "qwebchannel"

# FastAPI server settings
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765
PHONE_CAMERA_PORT = 8766

# Application settings
APP_NAME = "Dice Link"
APP_VERSION = "1.0.0"
DEBUG = True

# Camera settings
DEFAULT_CAMERA_INDEX = 0
CAMERA_FPS = 30
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Dice value ranges for validation
DICE_RANGES = {
    "d4": {"min": 1, "max": 4},
    "d6": {"min": 1, "max": 6},
    "d8": {"min": 1, "max": 8},
    "d10": {"min": 0, "max": 9},  # Can be 0-9 or 1-10 depending on die
    "d12": {"min": 1, "max": 12},
    "d20": {"min": 1, "max": 20},
    "d100": {"min": 1, "max": 100},
}
