"""
Local Storage Module

Handles persistent storage for user preferences, session history, and training data.
MVP: JSON file storage in AppData
Future: SQLite for session history and query capabilities
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def get_appdata_path():
    """
    Get the AppData directory for DLA.
    
    Returns:
        Path: Directory path (e.g., %APPDATA%/DiceLink)
    """
    if os.name == 'nt':  # Windows
        base = os.getenv('APPDATA', os.path.expanduser('~'))
    else:  # Mac/Linux (future)
        base = os.path.expanduser('~/.config')
    
    appdata_dir = Path(base) / 'DiceLink'
    appdata_dir.mkdir(parents=True, exist_ok=True)
    return appdata_dir


def get_config_path():
    """Get path to config.json file."""
    return get_appdata_path() / 'config.json'


def load_config():
    """
    Load user configuration from disk.
    
    Returns:
        dict: Configuration settings
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        # Return default config
        default_config = {
            'version': '1.0.0',
            'first_run': True,
            'data_collection_consent': None,  # None = not asked, True/False = user choice
            'model_version': None,
            'camera_index': 0,
            'websocket_port': 8765,
            'last_updated': None
        }
        save_config(default_config)
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Config loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def save_config(config):
    """
    Save user configuration to disk.
    
    Args:
        config (dict): Configuration settings
    """
    config_path = get_config_path()
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


def get_training_data_dir():
    """
    Get directory for storing training images.
    
    Returns:
        Path: training_data/ directory
    """
    training_dir = get_appdata_path() / 'training_data'
    training_dir.mkdir(parents=True, exist_ok=True)
    return training_dir


def save_training_sample(image_data, metadata):
    """
    Save a training sample (image + metadata) to disk.
    
    Args:
        image_data (bytes): JPEG image data
        metadata (dict): Roll metadata (dice type, result, timestamp, etc.)
    """
    # TODO: Implement training sample storage
    # Format: training_data/{timestamp}_{uuid}.jpg + .json
    logger.debug("Save training sample (stub)")
    pass


def get_models_dir():
    """
    Get directory for storing ONNX models.
    
    Returns:
        Path: models/ directory
    """
    models_dir = get_appdata_path() / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_current_model_path():
    """
    Get path to current ONNX model.
    
    Returns:
        Path: Path to dice_detection_v{version}.onnx
    """
    config = load_config()
    model_version = config.get('model_version', '1.0.0')
    return get_models_dir() / f'dice_detection_v{model_version}.onnx'


def load_window_size():
    """Return saved (width, height) tuple, or None if not previously saved."""
    config = load_config()
    w = config.get('window_width')
    h = config.get('window_height')
    if w and h:
        return (int(w), int(h))
    return None


def save_window_size(width, height):
    """Persist the main window size to config.json."""
    config = load_config()
    config['window_width'] = width
    config['window_height'] = height
    save_config(config)


# Future: SQLite session history functions
def init_session_db():
    """Initialize SQLite database for session history (v1.1+)."""
    pass


def save_roll_to_history(roll_data):
    """Save roll result to session history (v1.1+)."""
    pass


def get_session_history(limit=100):
    """Retrieve recent roll history (v1.1+)."""
    pass
