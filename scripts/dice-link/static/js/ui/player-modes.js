/**
 * Player Modes UI Module
 * Handles display and management of player modes (digital/manual/pending)
 * Only GM can approve/deny pending requests and revoke manual access
 */

let playerModesState = {
  isGM: false,
  globalOverride: 'individual',
  players: []
};

/**
 * Initialize player modes UI
 */
function initPlayerModes() {
  debugLog('Initializing Player Modes');
  
  // Check if user is GM (set when connection is established)
  const connectionState = getConnectionState();
  if (connectionState) {
    playerModesState.isGM = connectionState.isGM;
  }
  
  renderPlayerModes();
}

/**
 * Update player modes state from DLC message
 */
function updatePlayerModes(data) {
  debugLog('Updating Player Modes from DLC', data);
  
  playerModesState.isGM = data.isGM || playerModesState.isGM;
  playerModesState.globalOverride = data.globalOverride || 'individual';
  playerModesState.players = data.players || [];
  
  renderPlayerModes();
}

/**
 * Get the display mode for a player based on their mode and global override
 */
function getDisplayMode(player) {
  if (playerModesState.globalOverride === 'forceAllManual') {
    return 'manual';
  }
  if (playerModesState.globalOverride === 'forceAllDigital') {
    return 'digital';
  }
  return player.mode;
}

/**
 * Get the CSS variable color for a mode
 */
function getModeColor(mode) {
  const colors = {
    'digital': 'var(--dlc-digital)',
    'manual': 'var(--dlc-manual)',
    'pending': 'var(--dlc-pending)'
  };
  return colors[mode] || colors['pending'];
}

/**
 * Get the icon for a player mode
 */
function getModeIcon(mode) {
  const icons = {
    'digital': 'fas fa-dice',
    'manual': 'fas fa-hand-paper',
    'pending': 'fas fa-hourglass-half'
  };
  return icons[mode] || icons['pending'];
}

/**
 * Render the player modes section
 */
function renderPlayerModes() {
  const container = document.getElementById('player-modes-container');
  if (!container) {
    debugError('Player modes container not found');
    return;
  }
  
  if (!playerModesState.players || playerModesState.players.length === 0) {
    container.innerHTML = '<p class="player-modes-empty">No players connected</p>';
    return;
  }
  
  let html = '';
  
  playerModesState.players.forEach(player => {
    const displayMode = getDisplayMode(player);
    const modeColor = getModeColor(displayMode);
    const modeIcon = getModeIcon(displayMode);
    const isCurrentUser = player.id === (getConnectionState()?.userId);
    const showControls = playerModesState.isGM && player.mode === 'pending';
    const showRevokeBtn = playerModesState.isGM && player.mode === 'manual' && !isCurrentUser;
    
    html += `
      <div class="player-mode-item">
        <div class="player-mode-info">
          <i class="fas fa-user player-mode-avatar"></i>
          <div class="player-mode-details">
            <span class="player-name">${escapeHtml(player.name)}${isCurrentUser ? ' (You)' : ''}</span>
            <div class="player-mode-status">
              <i class="${modeIcon}" style="color: ${modeColor};"></i>
              <span class="mode-label">${displayMode.charAt(0).toUpperCase() + displayMode.slice(1)}</span>
            </div>
          </div>
        </div>
        
        <div class="player-mode-actions">
          ${showControls ? `
            <button class="btn btn-sm btn-success approve-mode-btn" data-player-id="${player.id}" title="Approve">
              <i class="fas fa-check"></i>
            </button>
            <button class="btn btn-sm btn-danger deny-mode-btn" data-player-id="${player.id}" title="Deny">
              <i class="fas fa-times"></i>
            </button>
          ` : ''}
          
          ${showRevokeBtn ? `
            <button class="btn btn-sm btn-danger revoke-mode-btn" data-player-id="${player.id}" title="Revoke manual mode">
              <i class="fas fa-ban"></i>
            </button>
          ` : ''}
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
  
  // Attach event listeners to action buttons
  attachPlayerModeEventListeners();
}

/**
 * Attach event listeners to player mode action buttons
 */
function attachPlayerModeEventListeners() {
  // Approve pending mode requests
  document.querySelectorAll('.approve-mode-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const playerId = btn.dataset.playerId;
      sendPlayerModeAction('approve', playerId);
    });
  });
  
  // Deny pending mode requests
  document.querySelectorAll('.deny-mode-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const playerId = btn.dataset.playerId;
      sendPlayerModeAction('deny', playerId);
    });
  });
  
  // Revoke manual mode access
  document.querySelectorAll('.revoke-mode-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const playerId = btn.dataset.playerId;
      sendPlayerModeAction('revoke', playerId);
    });
  });
}

/**
 * Send player mode action to DLC
 */
function sendPlayerModeAction(action, playerId) {
  debugLog(`Player mode action: ${action} for player ${playerId}`);
  
  const validActions = ['approve', 'deny', 'revoke'];
  if (!validActions.includes(action)) {
    debugError(`Invalid player mode action: ${action}`);
    return;
  }
  
  const message = {
    type: 'playerModeAction',
    action: action,
    playerId: playerId,
    timestamp: new Date().toISOString()
  };
  
  sendMessage(message);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Get player modes state for debugging
 */
function getPlayerModesState() {
  return playerModesState;
}
