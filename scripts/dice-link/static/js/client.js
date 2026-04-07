/**
 * Dice Link - Browser WebSocket Client (Modular Architecture)
 * Main entry point coordinating all modules
 * Phase 2: Enhanced UI with SVG dice icons, dice tray, and settings
 * Phase 3: Camera integration for dice roll capture (coming soon)
 */

/**
 * Main initialization function
 * Called when DOM is ready
 */
function init() {
  try {
    debugLog('=== Dice Link App Starting ===');
    
    // 1. Load saved settings
    loadSettings();
    
    // 2. Initialize UI modules
    initConnectionUI();
    initSettingsUI();
    initRollWindow();
    initDiceTray();
    
    // 3. Connect to WebSocket
    initWebSocket();
    
    debugLog('=== Dice Link App Ready ===');
  } catch (error) {
    debugError('Failed to initialize app', error);
  }
}

/**
 * Handle roll request from DLC
 */
function handleRollRequest(message) {
  debugLog('Received roll request from DLC', message);
  console.log('[v0] handleRollRequest called with:', JSON.stringify(message, null, 2));
  
  setCurrentRoll(message);
  
  // Render Roll Window request state
  console.log('[v0] About to call renderRWRequest');
  renderRWRequest(message);
  
  // Show Roll Window in request state
  console.log('[v0] About to call updateRollWindow("request")');
  updateRollWindow('request');
}

/**
 * Handle dice request from DLC (Phase B of roll)
 */
function handleDiceRequest(message) {
  debugLog('Received dice request from DLC', message);
  
  setPendingDiceRequest({
    originalRollId: message.originalRollId,
    rollType: message.rollType,
    formula: message.formula,
    dice: message.dice
  });
  
  // Render SVG dice entry UI
  const diceEntryHTML = renderDiceEntry(message);
  const elements = cacheElements();
  
  if (elements.rwDiceInputs) {
    elements.rwDiceInputs.innerHTML = diceEntryHTML;
  }
  
  // Initialize click handlers for dice entry
  initDiceEntry(message);
  
  // Show Roll Window in dice-entry state
  updateRollWindow('dice-entry');
}

/**
 * Start the app when DOM is ready
 */
document.addEventListener('DOMContentLoaded', init);

/**
 * Handle page visibility changes (pause/resume camera on tab switch, etc.)
 */
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    debugLog('Page hidden');
  } else {
    debugLog('Page visible');
  }
});
