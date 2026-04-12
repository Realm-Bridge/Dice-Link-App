// Player Modes UI Module
// Handles rendering and interaction for the Player Modes section

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize Player Modes UI
function initPlayerModes() {
    debugLog('[Player Modes] Initializing player modes UI');
    
    // Initial render with empty state
    renderPlayerModes();
    
    // Set up any needed listeners
    attachPlayerModeListeners();
}

// Update player modes from DLC message
function updatePlayerModes() {
    debugLog('[Player Modes] Updating player modes');
    renderPlayerModes();
}

// Main render function
function renderPlayerModes() {
    const playersGrid = document.getElementById('players-grid');
    const pendingSection = document.getElementById('pending-requests');
    const pendingList = document.getElementById('pending-list');
    const pendingCount = document.getElementById('pending-count');
    const noPlayers = document.getElementById('no-players');
    const modeLegend = document.querySelector('.mode-legend');
    
    if (!playersGrid || !pendingSection) {
        debugError('[Player Modes] Required elements not found');
        return;
    }
    
    const players = getPlayers();
    const isGM = getIsGM();
    const pendingRequests = players.filter(p => p.isPending);
    
    // Check if any player is a GM
    const hasGMPlayers = players.some(p => p.isGM);
    
    // Render mode legend with GM indicator if needed
    if (modeLegend) {
        let legendHTML = `
            <span class="legend-item">
                <span class="mode-dot digital"></span>Digital
            </span>
            <span class="legend-item">
                <span class="mode-dot manual"></span>Manual
            </span>
            <span class="legend-item">
                <span class="mode-dot pending"></span>Pending
            </span>
        `;
        
        if (hasGMPlayers) {
            legendHTML += `
            <span class="legend-item gm-indicator">
                <span class="mode-dot"></span>GM
            </span>
        `;
        }
        
        modeLegend.innerHTML = legendHTML;
    }
    
    // Render pending requests (GM only)
    if (isGM && pendingRequests.length > 0) {
        pendingSection.style.display = 'block';
        pendingCount.textContent = pendingRequests.length;
        pendingList.innerHTML = pendingRequests.map(player => `
            <div class="pending-item">
                <span class="pending-name">${escapeHtml(player.name)}</span>
                <div class="pending-actions">
                    <button class="btn btn-sm btn-success approve-btn" data-player-id="${escapeHtml(player.id)}">
                        <i class="fas fa-check"></i> Approve
                    </button>
                    <button class="btn btn-sm btn-danger deny-btn" data-player-id="${escapeHtml(player.id)}">
                        <i class="fas fa-times"></i> Deny
                    </button>
                </div>
            </div>
        `).join('');
        debugLog(`[Player Modes] Rendered ${pendingRequests.length} pending requests`);
    } else {
        pendingSection.style.display = 'none';
    }
    
    // Render players grid
    if (players.length === 0) {
        playersGrid.style.display = 'none';
        noPlayers.style.display = 'block';
        debugLog('[Player Modes] No players to display');
    } else {
        playersGrid.style.display = 'grid';
        noPlayers.style.display = 'none';
        
        playersGrid.innerHTML = players.map(player => {
            // Determine mode class: pending takes priority
            const modeClass = player.isPending ? 'pending' : player.mode;
            const gmClass = player.isGM ? 'is-gm' : '';
            
            return `
                <div class="player-card ${gmClass}">
                    <div class="player-info">
                        <span class="mode-dot ${modeClass}"></span>
                        <span class="player-name">${escapeHtml(player.name)}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        debugLog(`[Player Modes] Rendered ${players.length} players`);
    }
    
    // Attach event listeners
    attachPlayerModeListeners();
}

// Attach event listeners for action buttons
function attachPlayerModeListeners() {
    // Approve buttons
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.removeEventListener('click', handleApproveClick);
        btn.addEventListener('click', handleApproveClick);
    });
    
    // Deny buttons
    document.querySelectorAll('.deny-btn').forEach(btn => {
        btn.removeEventListener('click', handleDenyClick);
        btn.addEventListener('click', handleDenyClick);
    });
}

// Handle approve button click
function handleApproveClick(event) {
    const playerId = event.currentTarget.dataset.playerId;
    debugLog(`[Player Modes] Approving player: ${playerId}`);
    
    sendMessage({
        type: 'playerModeAction',
        action: 'approve',
        playerId: playerId
    });
}

// Handle deny button click
function handleDenyClick(event) {
    const playerId = event.currentTarget.dataset.playerId;
    debugLog(`[Player Modes] Denying player: ${playerId}`);
    
    sendMessage({
        type: 'playerModeAction',
        action: 'deny',
        playerId: playerId
    });
}
