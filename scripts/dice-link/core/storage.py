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
    """Create rolls.db with flat rolls table. Migrates old campaign/session schema automatically."""
    db_path = get_rolls_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        has_campaigns = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='campaigns'"
        ).fetchone() is not None

        if has_campaigns:
            _migrate_to_flat_schema(conn, cur)
        else:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rolls (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    die_type           TEXT NOT NULL,
                    value              INTEGER NOT NULL,
                    rolled_at          TEXT NOT NULL,
                    roll_label         TEXT NOT NULL DEFAULT '',
                    player_name        TEXT NOT NULL DEFAULT '',
                    world_title        TEXT NOT NULL DEFAULT '',
                    session_started_at TEXT NOT NULL DEFAULT ''
                );
            """)
            conn.commit()

        log_storage(f"Roll database ready at {db_path}")
    except Exception as e:
        log_storage(f"Failed to initialise roll database: {e}")
    finally:
        conn.close()


def _migrate_to_flat_schema(conn, cur):
    """Migrate from old campaigns/sessions/rolls schema to flat rolls table."""
    log_storage("Migrating database to flat schema...")
    for col_def in [
        "world_title TEXT NOT NULL DEFAULT ''",
        "session_started_at TEXT NOT NULL DEFAULT ''",
    ]:
        col_name = col_def.split()[0]
        try:
            conn.execute(f"ALTER TABLE rolls ADD COLUMN {col_def}")
            conn.commit()
            log_storage(f"Added column {col_name} to rolls")
        except sqlite3.OperationalError:
            pass

    conn.execute("""
        UPDATE rolls SET
            world_title = COALESCE(
                (SELECT c.world_title FROM campaigns c WHERE c.id = rolls.campaign_id), ''
            ),
            session_started_at = COALESCE(
                (SELECT s.started_at FROM sessions s WHERE s.id = rolls.session_id), ''
            )
        WHERE world_title = '' OR session_started_at = ''
    """)
    conn.commit()
    log_storage("Backfilled world_title and session_started_at on all rolls")

    try:
        conn.execute("DROP TABLE IF EXISTS sessions")
        conn.execute("DROP TABLE IF EXISTS campaigns")
        conn.commit()
        log_storage("Dropped campaigns and sessions tables")
    except Exception as e:
        log_storage(f"Could not drop old tables (non-critical): {e}")


def start_session(world_title):
    """Record session start. Returns session_started_at timestamp string."""
    now = datetime.now().isoformat()
    log_storage(f"Started session for '{world_title}' at {now}")
    return now


def save_roll_to_history(world_title, session_started_at, die_type, value, roll_label='', player_name=''):
    """Save one die result to the rolls table."""
    db_path = get_rolls_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO rolls (die_type, value, rolled_at, roll_label, player_name, world_title, session_started_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (die_type, int(value), now, roll_label, player_name, world_title, session_started_at)
        )
        conn.commit()
        log_storage(f"Saved roll: {die_type}={value} label='{roll_label}' player='{player_name}' world='{world_title}'")
    except Exception as e:
        log_storage(f"Failed to save roll to history: {e}")
    finally:
        conn.close()


# ── Roll Stats ────────────────────────────────────────────────────────────────

def _empty_roll_stats():
    return {
        'distribution': {}, 'total': 0, 'average': 0,
        'highest': 0, 'lowest': 0, 'labels': [], 'players': [], 'worlds': [],
    }


def _resolve_session_scope(cur, scope):
    """Return list of session_started_at values for a scope string, or None meaning 'all'."""
    if not scope or scope == 'all':
        return None
    if scope == 'current':
        from state import app_state
        sat = app_state.current_session_started_at
        return [sat] if sat is not None else []
    n = {'last1': 1, 'last5': 5, 'last10': 10}.get(scope)
    if n:
        from state import app_state
        current_sat = app_state.current_session_started_at
        if n == 1 and current_sat is not None:
            rows = cur.execute(
                'SELECT DISTINCT session_started_at FROM rolls '
                'WHERE session_started_at != ? ORDER BY session_started_at DESC LIMIT 1',
                (current_sat,)
            ).fetchall()
        else:
            rows = cur.execute(
                'SELECT DISTINCT session_started_at FROM rolls ORDER BY session_started_at DESC LIMIT ?',
                (n,)
            ).fetchall()
        return [r[0] for r in rows]
    return None


def _build_roll_where(die_types, world_names, session_sats, player_names, label_filter,
                      inc_players=True, inc_labels=True):
    """Return (where_clause, params) for the rolls table aliased as r."""
    conds, params = [], []
    if die_types and die_types != ['all']:
        conds.append(f'r.die_type IN ({",".join("?" * len(die_types))})')
        params.extend(die_types)
    if world_names and world_names != ['all']:
        conds.append(f'r.world_title IN ({",".join("?" * len(world_names))})')
        params.extend(world_names)
    if session_sats is not None:
        if not session_sats:
            return 'WHERE 1=0', []
        conds.append(f'r.session_started_at IN ({",".join("?" * len(session_sats))})')
        params.extend(session_sats)
    if inc_players and player_names and player_names != ['all']:
        conds.append(f'r.player_name IN ({",".join("?" * len(player_names))})')
        params.extend(player_names)
    if inc_labels and label_filter and label_filter != ['all']:
        sub = ' OR '.join('r.roll_label LIKE ?' for _ in label_filter)
        conds.append(f'({sub})')
        params.extend(f'%{lf}%' for lf in label_filter)
    where = ('WHERE ' + ' AND '.join(conds)) if conds else ''
    return where, params


def query_roll_stats(die_types=None, world_names=None, session_scope='all',
                     player_names=None, label_filter=None):
    """Return stats dict for rolls matching the given filters."""
    db_path = get_rolls_db_path()
    if not os.path.exists(str(db_path)):
        return _empty_roll_stats()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        session_sats = _resolve_session_scope(cur, session_scope)
        where, params = _build_roll_where(die_types, world_names, session_sats, player_names, label_filter)

        cur.execute(f'SELECT r.value, COUNT(*) c FROM rolls r {where} GROUP BY r.value ORDER BY r.value', params)
        distribution = {str(r['value']): r['c'] for r in cur.fetchall()}

        cur.execute(f'SELECT COUNT(*) total, AVG(r.value) avg, MAX(r.value) hi, MIN(r.value) lo FROM rolls r {where}', params)
        agg = cur.fetchone()
        total   = agg['total'] or 0
        average = round(agg['avg'], 2) if agg['avg'] is not None else 0
        highest = agg['hi']  or 0
        lowest  = agg['lo']  or 0

        wl, pl = _build_roll_where(die_types, world_names, session_sats, player_names, label_filter, inc_labels=False)
        cur.execute(f'SELECT DISTINCT r.roll_label l FROM rolls r {wl} ORDER BY r.roll_label', pl)
        labels = [r['l'] for r in cur.fetchall() if r['l']]

        wp, pp = _build_roll_where(die_types, world_names, session_sats, player_names, label_filter, inc_players=False, inc_labels=False)
        cur.execute(f'SELECT DISTINCT r.player_name p FROM rolls r {wp} ORDER BY r.player_name', pp)
        players = [r['p'] for r in cur.fetchall() if r['p']]

        cur.execute("SELECT DISTINCT world_title FROM rolls WHERE world_title != '' ORDER BY world_title")
        worlds = [r['world_title'] for r in cur.fetchall()]

        return {
            'distribution': distribution, 'total': total, 'average': average,
            'highest': highest, 'lowest': lowest,
            'labels': labels, 'players': players, 'worlds': worlds,
        }
    except Exception as e:
        log_storage(f"Failed to query roll stats: {e}")
        return _empty_roll_stats()
    finally:
        conn.close()


def delete_rolls(die_types=None, world_names=None, session_scope='all',
                 player_names=None, label_filter=None):
    """Delete rolls matching the given filters. Returns count of deleted rows."""
    db_path = get_rolls_db_path()
    if not os.path.exists(str(db_path)):
        return 0
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        session_sats = _resolve_session_scope(cur, session_scope)
        conds, params = [], []
        if die_types and die_types != ['all']:
            conds.append(f'die_type IN ({",".join("?" * len(die_types))})')
            params.extend(die_types)
        if world_names and world_names != ['all']:
            conds.append(f'world_title IN ({",".join("?" * len(world_names))})')
            params.extend(world_names)
        if session_sats is not None:
            if not session_sats:
                return 0
            conds.append(f'session_started_at IN ({",".join("?" * len(session_sats))})')
            params.extend(session_sats)
        if player_names and player_names != ['all']:
            conds.append(f'player_name IN ({",".join("?" * len(player_names))})')
            params.extend(player_names)
        if label_filter and label_filter != ['all']:
            sub = ' OR '.join('roll_label LIKE ?' for _ in label_filter)
            conds.append(f'({sub})')
            params.extend(f'%{lf}%' for lf in label_filter)
        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''
        cur.execute(f'DELETE FROM rolls {where}', params)
        conn.commit()
        deleted = cur.rowcount
        log_storage(f"Deleted {deleted} rolls")
        return deleted
    except Exception as e:
        log_storage(f"Failed to delete rolls: {e}")
        return 0
    finally:
        conn.close()


def get_rolls_for_export():
    """Return all rolls as list of dicts for CSV export."""
    db_path = get_rolls_db_path()
    if not os.path.exists(str(db_path)):
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT rolled_at, player_name, die_type, value, roll_label, world_title, session_started_at '
            'FROM rolls ORDER BY rolled_at'
        )
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        log_storage(f"Failed to get rolls for export: {e}")
        return []
    finally:
        conn.close()


def import_rolls_from_csv(rows):
    """Import roll rows (list of dicts) from CSV. Skips duplicates.
    De-dup key: rolled_at + player_name + die_type + value.
    session_started_at is optional — falls back to rolled_at for old-format exports."""
    db_path = get_rolls_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    imported = skipped = 0
    try:
        cur = conn.cursor()
        for row in rows:
            world_title = row.get('world_title', '').strip()
            if not world_title:
                skipped += 1
                continue

            rolled_at   = row.get('rolled_at', '')
            player_name = row.get('player_name', '')
            die_type    = row.get('die_type', '')
            value       = int(row.get('value', 0))
            roll_label  = row.get('roll_label', '')
            session_started_at = row.get('session_started_at', '').strip() or rolled_at

            if cur.execute(
                "SELECT id FROM rolls WHERE rolled_at=? AND player_name=? AND die_type=? AND value=?",
                (rolled_at, player_name, die_type, value)
            ).fetchone():
                skipped += 1
                continue

            cur.execute(
                "INSERT INTO rolls (die_type, value, rolled_at, roll_label, player_name, world_title, session_started_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (die_type, value, rolled_at, roll_label, player_name, world_title, session_started_at)
            )
            imported += 1
        conn.commit()
        log_storage(f"Imported {imported} rolls, skipped {skipped} duplicates")
        return {'imported': imported, 'skipped': skipped, 'error': None}
    except Exception as e:
        log_storage(f"Failed to import rolls: {e}")
        return {'imported': 0, 'skipped': 0, 'error': str(e)}
    finally:
        conn.close()
