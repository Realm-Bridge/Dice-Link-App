/**
 * Debug Logging Utility
 * Provides consistent debug output that appears in the command prompt
 * via the server.py debug message handler (type: "debug").
 * Falls back to console.log if WebSocket is not yet available.
 */

// Debug mode toggle - set to false for production
let DEBUG_ENABLED = true;

/**
 * Send a log message to the command prompt via WebSocket.
 * server.py handles type:"debug" and prints: [JS] <message>
 * @param {string} level - 'log' | 'error' | 'warn'
 * @param {string} message - Message to send
 * @param {*} data - Optional data to include
 */
function debugSend(level, message, data = null) {
  const timestamp = new Date().toLocaleTimeString();
  const dataStr = data !== null ? ' ' + JSON.stringify(data) : '';
  const fullMessage = `[DLA ${level.toUpperCase()} ${timestamp}] ${message}${dataStr}`;

  // Always mirror to browser console as a fallback
  if (level === 'error') {
    console.error(fullMessage);
  } else {
    console.log(fullMessage);
  }

  // Send to server command prompt via WebSocket if available
  // getWebSocket() is provided by websocket.js
  if (typeof getWebSocket === 'function') {
    const ws = getWebSocket();
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'debug', message: fullMessage }));
      } catch (e) {
        // Silently ignore send failures during debug
      }
    }
  }
}

/**
 * Log a debug message
 * @param {string} message - Message to log
 * @param {*} data - Optional data to log
 */
function debugLog(message, data = null) {
  if (!DEBUG_ENABLED) return;
  debugSend('log', message, data);
}

/**
 * Log an error message
 * @param {string} message - Error message
 * @param {*} error - Optional error object or data
 */
function debugError(message, error = null) {
  if (!DEBUG_ENABLED) return;
  debugSend('error', message, error ? (error.message || error) : null);
}

/**
 * Enable or disable debug logging
 * @param {boolean} enabled - True to enable, false to disable
 */
function setDebugEnabled(enabled) {
  DEBUG_ENABLED = enabled;
  debugLog(`Debug logging ${enabled ? 'enabled' : 'disabled'}`);
}

/**
 * Check if debug is enabled
 * @returns {boolean}
 */
function isDebugEnabled() {
  return DEBUG_ENABLED;
}
