/**
 * Player Modes UI Module
 * Displays player list with their dice rolling modes
 * GM-only controls for approve/deny/revoke actions
 */

// Cache DOM elements
let pmElements = null;

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize Player Modes UI
 */
function initPlayerModes() {
    pmElements = {
        section: document.getElementById('player-modes-section'),
        container: document.getElementById('player-modes-container')
    };
    
    debugLog('Player Modes UI initialized');
}

/**
 * Update Player Modes UI
 * Called when playerModesUpdate message is received
 */
function updatePlayerModes() {
    if (!pmElements || !pmElements.container) {
        debugError('Player modes container not found');
        return;
    }
    
    const players = getPlayers();
    const globalOverride = getGlobalOverride();
    const isGM = getIsGM();
    
    debugLog('Updating player modes UI', { 
        playerCount: players.length, 
        globalOverride, 
        isGM 
    });
    
    renderPlayers(players, globalOverride, isGM);
}

/**
 * Render the players list
 */
function renderPlayers(players, globalOverride, isGM) {
    const container = pmElements.container;
    
    if (!players || players.length === 0) {
        container.innerHTML = '<p class="player-modes-empty">No players connected</p>';
        return;
    }
    
    let html = '';
    
    for (const player of players) {
        // Determine effective mode based on global override
        let effectiveMode = player.mode;
        if (globalOverride === 'forceAllManual') {
            effectiveMode = 'manual';
        } else if (globalOverride === 'forceAllDigital') {
            effectiveMode = 'digital';
        }
        
        // Get mode display info
        const modeInfo = getModeDisplayInfo(effectiveMode);
        
        // Build player card HTML
        html += `
            <div class="player-mode-item" data-player-id="${escapeHtml(player.odooId || player.odoo_id || '')}">
                <div class="player-mode-info">
                    <span class="player-mode-avatar">
                        <i class="fas fa-user"></i>
                    </span>
                    <div class="player-mode-details">
                        <span class="player-name">${escapeHtml(player.displayName || player.name || 'Unknown')}</span>
                        <span class="player-mode-status ${modeInfo.className}">
                            <i class="${modeInfo.icon}"></i>
                            ${modeInfo.label}
                        </span>
                    </div>
                </div>
                ${renderActionButtons(player, isGM)}
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Attach event listeners to action buttons
    attachActionListeners();
}

/**
 * Get display info for a mode
 */
function getModeDisplayInfo(mode) {
    switch (mode) {
        case 'digital':
            return {
                className: 'digital',
                icon: 'fas fa-dice',
                label: 'Digital'
            };
        case 'manual':
            return {
                className: 'manual',
                icon: 'fas fa-hand-paper',
                label: 'Manual'
            };
        case 'pending':
            return {
                className: 'pending',
                icon: 'fas fa-clock',
                label: 'Pending'
            };
        default:
            return {
                className: 'digital',
                icon: 'fas fa-dice',
                label: 'Digital'
            };
    }
}

/**
 * Render action buttons for a player (GM only)
 */
function renderActionButtons(player, isGM) {
    if (!isGM) {
        return '';
    }
    
    const mode = player.mode;
    
    // Pending mode: show approve/deny buttons
    if (mode === 'pending') {
        return `
            <div class="player-mode-actions">
                <button class="btn-sm btn-success pm-action-btn" data-action="approve" data-player-id="${escapeHtml(player.odooId || player.odoo_id || '')}" title="Approve manual mode">
                    <i class="fas fa-check"></i>
                </button>
                <button class="btn-sm btn-danger pm-action-btn" data-action="deny" data-player-id="${escapeHtml(player.odooId || player.odoo_id || '')}" title="Deny manual mode">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }
    
    // Manual mode: show revoke button
    if (mode === 'manual') {
        return `
            <div class="player-mode-actions">
                <button class="btn-sm btn-danger pm-action-btn" data-action="revoke" data-player-id="${escapeHtml(player.odooId || player.odoo_id || '')}" title="Revoke manual mode">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }
    
    // Digital mode: no actions needed
    return '';
}

/**
 * Attach event listeners to action buttons
 */
function attachActionListeners() {
    const buttons = document.querySelectorAll('.pm-action-btn');
    
    buttons.forEach(btn => {
        btn.addEventListener('click', handleActionClick);
    });
}

/**
 * Handle action button click
 */
function handleActionClick(event) {
    const button = event.currentTarget;
    const action = button.dataset.action;
    const odooId = button.dataset.playerId;
    
    if (!action || !odooId) {
        debugError('Missing action or player ID', { action, odooId });
        return;
    }
    
    debugLog('Player mode action', { action, odooId });
    
    // Send playerModeAction message to DLC
    sendMessage({
        type: 'playerModeAction',
        action: action,
        odooId: odooId
    });
}
