/**
 * Utility Functions
 * Shared helper functions used across modules
 */

/**
 * Get the path to a dice SVG icon
 * @param {string} dieType - e.g., "d20", "d6"
 * @param {number|null} value - The rolled value, or null for blank
 * @returns {string} Path to SVG file
 */
function getDiceIconPath(dieType, value = null) {
    const type = dieType.toLowerCase();
    // Folder name is uppercase (D4, D6, etc.)
    const folder = type.toUpperCase();
    
    let filename;
    if (value !== null && value !== undefined) {
        // Return numbered icon if it exists (d100 only has blank)
        if (type === 'd100') {
            filename = `${type}-blank.svg`;
        } else {
            // Numbered files have format "d20 - Outline 1.svg"
            filename = `${type} - Outline ${value}.svg`;
        }
    } else {
        filename = `${type}-blank.svg`;
    }
    
    // Build path - spaces are OK in modern browsers and FastAPI handles them
    const path = `/static/DLC Dice/${folder}/${filename}`;
    debugLog(`getDiceIconPath(${dieType}, ${value}) => ${path}`);
    return path;
}

/**
 * Cache DOM elements for repeated access
 * @returns {Object} Cached element references
 */
function cacheElements() {
    return {
        // Main windows
        rollWindow: document.getElementById('roll-window'),
        waitingState: document.getElementById('roll-window-waiting'),
        idleState: document.getElementById('roll-window-idle'),
        requestState: document.getElementById('roll-window-request'),
        diceEntryState: document.getElementById('roll-window-dice-entry'),
        
        // Roll window sections
        rwTitle: document.getElementById('rw-title'),
        rwSubtitle: document.getElementById('rw-subtitle'),
        rwConfigSection: document.getElementById('rw-config-section'),
        rwButtons: document.getElementById('rw-action-buttons'),
        rwDiceInputs: document.getElementById('rw-dice-inputs'),
        cancelRoll: document.getElementById('rw-cancel-btn'),
        
        // Settings
        settingsBtn: document.getElementById('settings-btn'),
        settingsPanel: document.getElementById('settings-panel'),
        hostInput: document.getElementById('host-input'),
        portInput: document.getElementById('port-input'),
        
        // Connection status
        connectionStatus: document.getElementById('connection-status'),
        connectionText: document.getElementById('connection-status-text'),
        
        // Camera (Phase 3)
        cameraFeed: document.getElementById('camera-feed'),
        cameraButton: document.getElementById('camera-btn'),
        
        // Old panels (deprecated, kept for legacy support)
        rollPanel: document.getElementById('roll-panel'),
        diceEntryPanel: document.getElementById('dice-entry-panel'),
        completeState: document.getElementById('complete-state'),
        configFields: document.getElementById('config-fields'),
        selectedAction: document.getElementById('selected-action')
    };
}

/**
 * Format milliseconds to readable time
 * @param {number} ms - Milliseconds
 * @returns {string} Formatted time string
 */
function formatTime(ms) {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Parse connection string from settings
 * @param {Object} settings - Settings object
 * @returns {string} Connection URL
 */
function getConnectionUrl(settings) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${settings.host}:${settings.port}/ws/ui`;
}
