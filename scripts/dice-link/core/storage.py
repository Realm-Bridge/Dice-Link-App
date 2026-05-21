"""
Local Storage Module

Handles persistent storage for user preferences, session history, and training data.
MVP: JSON file storage in AppData
Future: SQLite for session history and query capabilities
"""

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime

from debug import log_storage


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
        default_config = {
            'version': '1.0.0',
            'first_run': True,
            'data_collection_consent': None,
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
        return config
    except Exception as e:
        log_storage(f"Failed to load config: {e}")
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
    except Exception as e:
        log_storage(f"Failed to save config: {e}")


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
    """Save a training sample (image + metadata) to disk. Stub — not yet implemented."""
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


def get_rolls_db_path():
    """Get path to rolls.db SQLite database."""
    return get_appdata_path() / 'rolls.db'


def init_roll_db():
    """Create rolls.db with campaigns, sessions, and rolls tables if they don't exist.
    Also migrates existing databases to add any new columns."""
    db_path = get_rolls_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id TEXT NOT NULL UNIQUE,
                world_title TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                started_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                die_type TEXT NOT NULL,
                value INTEGER NOT NULL,
                rolled_at TEXT NOT NULL,
                roll_label TEXT NOT NULL DEFAULT ''
            );
        """)
        conn.commit()

        # Migrate existing databases — add columns introduced after initial release
        for col_def in ["roll_label TEXT NOT NULL DEFAULT ''"]:
            col_name = col_def.split()[0]
            try:
                conn.execute(f"ALTER TABLE rolls ADD COLUMN {col_def}")
                conn.commit()
                log_storage(f"Migrated rolls table: added column {col_name}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        log_storage(f"Roll database ready at {db_path}")
    except Exception as e:
        log_storage(f"Failed to initialise roll database: {e}")
    finally:
        conn.close()


def start_session(world_id, world_title):
    """
    Get or create the campaign for this world, then open a new session.
    Returns the new session id (int).
    """
    db_path = get_rolls_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO campaigns (world_id, world_title) VALUES (?, ?) "
            "ON CONFLICT(world_id) DO UPDATE SET world_title = excluded.world_title",
            (world_id, world_title)
        )
        row = conn.execute(
            "SELECT id FROM campaigns WHERE world_id = ?", (world_id,)
        ).fetchone()
        campaign_id = row[0]

        now = datetime.utcnow().isoformat()
        cursor = conn.execute(
            "INSERT INTO sessions (campaign_id, started_at) VALUES (?, ?)",
            (campaign_id, now)
        )
        session_id = cursor.lastrowid
        conn.commit()
        log_storage(f"Started session {session_id} for campaign '{world_title}' (world_id={world_id})")
        return session_id
    except Exception as e:
        log_storage(f"Failed to start session: {e}")
        return None
    finally:
        conn.close()


def save_roll_to_history(session_id, die_type, value, roll_label=''):
    """Save one die result to the rolls table."""
    db_path = get_rolls_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT campaign_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            log_storage(f"save_roll_to_history: session {session_id} not found")
            return
        campaign_id = row[0]
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO rolls (session_id, campaign_id, die_type, value, rolled_at, roll_label) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, campaign_id, die_type, int(value), now, roll_label)
        )
        conn.commit()
        log_storage(f"Saved roll: {die_type}={value} label='{roll_label}' (session={session_id}, campaign={campaign_id})")
    except Exception as e:
        log_storage(f"Failed to save roll to history: {e}")
    finally:
        conn.close()


def get_session_history(limit=100):
    """Retrieve recent roll history (v1.1+)."""
    pass
