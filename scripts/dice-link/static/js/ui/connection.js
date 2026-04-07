/**
 * Connection Status UI Module
 * Displays connection state and player information
 */

/**
 * Initialize connection status UI
 */
function initConnectionUI() {
  debugLog('Initializing connection UI');
  // Connection UI initialization - status updates are handled by websocket.js
}

/**
 * Update connection status display
 */
function updateConnectionStatusDisplay(connected, playerName) {
  const elements = cacheElements();
  const statusElement = elements.connectionStatus;
  const statusText = elements.connectionText;
  
  if (!statusElement || !statusText) {
    debugLog('Connection status elements not found');
    return;
  }
  
  if (connected) {
    statusElement.classList.remove('disconnected');
    statusElement.classList.add('connected');
    statusText.textContent = playerName ? `Connected: ${playerName}` : 'Connected';
    debugLog(`Connected as ${playerName || 'Unknown Player'}`);
  } else {
    statusElement.classList.remove('connected');
    statusElement.classList.add('disconnected');
    statusText.textContent = 'Disconnected';
    debugLog('Connection lost');
  }
}
