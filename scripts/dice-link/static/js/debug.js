/**
 * Debug Logging Utility
 * Provides consistent debug output with toggle for development/production
 */

// Debug mode toggle - set to false for production
let DEBUG_ENABLED = true;

/**
 * Log a debug message to console
 * @param {string} message - Message to log
 * @param {*} data - Optional data to log
 */
function debugLog(message, data = null) {
  if (!DEBUG_ENABLED) return;
  
  const timestamp = new Date().toLocaleTimeString();
  const prefix = `[DLA ${timestamp}]`;
  
  if (data !== null) {
    console.log(`${prefix} ${message}`, data);
  } else {
    console.log(`${prefix} ${message}`);
  }
}

/**
 * Log an error message
 * @param {string} message - Error message
 * @param {Error} error - Optional error object
 */
function debugError(message, error = null) {
  if (!DEBUG_ENABLED) return;
  
  const timestamp = new Date().toLocaleTimeString();
  const prefix = `[DLA ERROR ${timestamp}]`;
  
  if (error) {
    console.error(`${prefix} ${message}`, error);
  } else {
    console.error(`${prefix} ${message}`);
  }
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
