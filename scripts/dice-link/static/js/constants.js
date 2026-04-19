/**
 * Application Constants
 * Dice ranges, defaults, connection settings
 */

// Dice value ranges for validation
const DICE_RANGES = {
    d4: { min: 1, max: 4 },
    d6: { min: 1, max: 6 },
    d8: { min: 1, max: 8 },
    d10: { min: 1, max: 10 },
    d12: { min: 1, max: 12 },
    d20: { min: 1, max: 20 },
    d100: { min: 1, max: 100 }
};

// Default application settings
const DEFAULT_SETTINGS = {
    host: 'localhost',
    port: 8765,
    theme: 'dark',
    cameraIndex: 0
};

// Connection constants
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 2000; // milliseconds

// Dice ordering for formula building
const DICE_ORDER = [4, 6, 8, 10, 12, 20, 100];

// Storage keys for persisting settings
const STORAGE_KEYS = {
    SETTINGS: 'dicelink_settings',
    CAMERA_INDEX: 'dicelink_camera_index'
};
