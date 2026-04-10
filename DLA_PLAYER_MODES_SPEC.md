# DLA Player Modes Implementation Specification

## Overview

Move the Player Modes functionality from DLC to DLA. This section displays all connected users (including GM) and their dice rolling mode (digital/manual/pending), and provides GM controls for managing player permissions.

**Important:** DLA already receives `isGM` from DLC's connect message. Use this to show/hide GM-only controls (approve/deny buttons).

## Communication Requirements

### New Messages from DLC to DLA

DLC sends player mode data to DLA when connecting and whenever modes change. **The `players` array includes all users - both players and the GM - so everyone can see each other's modes:**

```json
{
  "type": "playerModesUpdate",
  "globalOverride": "individual",  // "individual" | "forceAllManual" | "forceAllDigital" (read-only in DLA)
  "players": [
    {
      "id": "gm123",
      "name": "Gamemaster",
      "mode": "manual",           // "digital" | "manual"
      "storedMode": "manual",     // Original mode before override
      "isPending": false,
      "isGM": true                // Indicates this is the GM (optional, for display purposes)
    },
    {
      "id": "player123",
      "name": "Alice",
      "mode": "manual",
      "storedMode": "manual",
      "isPending": false,
      "isGM": false
    },
    {
      "id": "player456", 
      "name": "Bob",
      "mode": "digital",
      "storedMode": "digital",
      "isPending": true,
      "isGM": false
    }
  ],
  "pendingRequests": [
    { "playerId": "player456", "playerName": "Bob" }
  ]
}
```

### New Messages from DLA to DLC

**Only for approval/denial of pending requests. Global override is controlled in DLC settings only.**

```json
// Approve manual dice request
{ "type": "playerModeAction", "action": "approve", "playerId": "player456" }

// Deny manual dice request  
{ "type": "playerModeAction", "action": "deny", "playerId": "player456" }
```

---

## State Management

Add to DLA's state object:

```javascript
const state = {
    // ... existing properties ...
    
    // Player modes
    isGM: false,                    // Set from connect message
    globalOverride: 'individual',   // Current override mode
    players: [],                    // Array of player objects
    pendingRequests: []             // Array of pending approval requests
};
```

---

## HTML Structure

### Player Modes Section (Dashboard Component)

```html
<!-- Player Modes Section - always visible on dashboard -->
<div class="player-modes-section" id="player-modes-section">
  <div class="section-header">
    <h3><i class="fas fa-users"></i> Player Modes</h3>
  </div>
  
  <div class="section-content">
    <!-- Legend -->
    <div class="mode-legend">
      <span class="legend-item"><span class="mode-dot digital"></span>Digital</span>
      <span class="legend-item"><span class="mode-dot manual"></span>Manual</span>
      <span class="legend-item"><span class="mode-dot pending"></span>Pending</span>
    </div>
    
    <!-- Pending Requests (GM only) -->
    <div class="pending-requests" id="pending-requests" style="display: none;">
      <h4><i class="fas fa-clock"></i> Pending Requests (<span id="pending-count">0</span>)</h4>
      <div class="pending-list" id="pending-list">
        <!-- Populated dynamically -->
      </div>
    </div>
    
    <!-- Player Grid -->
    <div class="players-grid" id="players-grid">
      <!-- Populated dynamically -->
    </div>
    
    <!-- No Players Message -->
    <p class="no-players" id="no-players" style="display: none;">No players connected.</p>
  </div>
</div>
```

### Pending Request Item (GM only)

```html
<div class="pending-item">
  <span class="pending-name">Bob</span>
  <div class="pending-actions">
    <button class="btn btn-sm btn-success approve-btn" data-player-id="player456">
      <i class="fas fa-check"></i> Approve
    </button>
    <button class="btn btn-sm btn-danger deny-btn" data-player-id="player456">
      <i class="fas fa-times"></i> Deny
    </button>
  </div>
</div>
```

### Player Card

```html
<!-- Standard player card -->
<div class="player-card">
  <div class="player-info">
    <span class="mode-dot manual"></span>
    <span class="player-name">Alice</span>
  </div>
</div>

<!-- Player card (simple - no revoke) -->
<div class="player-card">
  <div class="player-info">
    <span class="mode-dot manual"></span>
    <span class="player-name">Alice</span>
  </div>
  <div class="player-status">Manual</div>
</div>
```

---

## CSS Styling

Uses the same color variables from DLC (already in DLA from previous specs):

```css
/* ============================================================================
   PLAYER MODES SECTION
   ============================================================================ */

.player-modes-section {
  background: var(--dlc-bg-section);
  border: 1px solid var(--dlc-border);
  border-radius: 8px;
  padding: 12px;
}

.player-modes-section .section-header {
  margin-bottom: 12px;
}

.player-modes-section .section-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--dlc-text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.player-modes-section .section-header h3 i {
  color: var(--dlc-accent);
}

/* ============================================================================
   MODE LEGEND
   ============================================================================ */

.mode-legend {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  padding: 6px 10px;
  background: var(--dlc-bg-input);
  border-radius: 4px;
  font-size: 10px;
  color: var(--dlc-text-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Color dots for mode indication */
.mode-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.mode-dot.digital {
  background: var(--dlc-digital);
  box-shadow: 0 0 4px var(--dlc-digital);
}

.mode-dot.manual {
  background: var(--dlc-success);
  box-shadow: 0 0 4px var(--dlc-success);
}

.mode-dot.pending {
  background: var(--dlc-warning);
  box-shadow: 0 0 4px var(--dlc-warning);
}

/* Legend uses smaller dots */
.legend-item .mode-dot {
  width: 8px;
  height: 8px;
}

/* Revoke dot in legend */
.mode-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

.mode-dot.digital {
  background-color: var(--dlc-digital, #6366f1);
}

.mode-dot.manual {
  background-color: var(--dlc-manual, #10b981);
}

.mode-dot.pending {
  background-color: var(--dlc-warning, #D5D5D6);
}

.revoke-dot::after {
  content: "\00D7";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 6px;
  font-weight: bold;
  color: #1a1a1a;
  line-height: 1;
}

/* ============================================================================
   PENDING REQUESTS (GM ONLY)
   ============================================================================ */

.pending-requests {
  margin-bottom: 12px;
  padding: 10px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid var(--dlc-warning);
  border-radius: 6px;
}

.pending-requests h4 {
  font-size: 12px;
  font-weight: 600;
  color: var(--dlc-warning);
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.pending-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pending-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: var(--dlc-bg-input);
  border: 1px solid var(--dlc-warning);
  border-radius: 6px;
}

.pending-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--dlc-text-primary);
}

.pending-actions {
  display: flex;
  gap: 6px;
}

/* ============================================================================
   PLAYERS GRID
   ============================================================================ */

.players-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
  align-items: stretch;
  grid-auto-rows: 52px;
}

.player-card {
  background-color: var(--dlc-bg-section, #2a3547);
  border: 1px solid var(--dlc-border, #6f2e9a);
  border-radius: 4px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.player-card:hover {
  border-color: var(--dlc-accent-pink, #a78bfa);
}

.player-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.player-name {
  color: var(--dlc-text-primary, #e7f6ff);
  font-weight: 500;
}

.player-status {
  color: var(--dlc-text-secondary, #a0a0b0);
  font-size: 12px;
}

.player-card:hover {
  border-color: var(--dlc-accent);
}

.player-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.player-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--dlc-text-primary);
  word-break: break-word;
  overflow-wrap: break-word;
  hyphens: auto;
  min-width: 0;
}

/* Revokable card */
.player-card-revokable {
  position: relative;
  overflow: visible;
}

/* Small X icon pinned to top-right corner */
.revoke-corner {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--dlc-warning);
  color: #1a1a1a;
  border: 1px solid var(--dlc-bg-dark);
  font-size: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease;
  padding: 0;
  line-height: 1;
  z-index: 2;
}

.revoke-corner:hover {
  background: var(--dlc-warning-hover);
  transform: scale(1.2);
}

/* No players message */
.no-players {
  text-align: center;
  padding: 20px;
  color: var(--dlc-text-muted);
  font-style: italic;
  font-size: 12px;
  margin: 0;
}

/* ============================================================================
   BUTTONS
   ============================================================================ */

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 10px;
}

.btn-success {
  background: var(--dlc-success);
  color: white;
}

.btn-success:hover {
  background: var(--dlc-success-hover);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

.btn-danger {
  background: var(--dlc-danger);
  color: white;
}

.btn-danger:hover {
  background: var(--dlc-danger-hover);
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.4);
}
```

---

## JavaScript Implementation

### Handle playerModesUpdate Message

```javascript
function handlePlayerModesUpdate(message) {
    state.globalOverride = message.globalOverride;
    state.players = message.players;
    state.pendingRequests = message.pendingRequests || [];
    
    renderPlayerModes();
}

// Add to message handler switch
case 'playerModesUpdate':
    handlePlayerModesUpdate(message);
    break;
```

### Render Player Modes

```javascript
function renderPlayerModes() {
    const playersGrid = document.getElementById('players-grid');
    const pendingSection = document.getElementById('pending-requests');
    const pendingList = document.getElementById('pending-list');
    const pendingCount = document.getElementById('pending-count');
    const noPlayers = document.getElementById('no-players');
    
    // Render pending requests (GM only)
    if (state.isGM && state.pendingRequests.length > 0) {
        pendingSection.style.display = 'block';
        pendingCount.textContent = state.pendingRequests.length;
        pendingList.innerHTML = state.pendingRequests.map(req => `
            <div class="pending-item">
                <span class="pending-name">${escapeHtml(req.playerName)}</span>
                <div class="pending-actions">
                    <button class="btn btn-sm btn-success approve-btn" data-player-id="${req.playerId}">
                        <i class="fas fa-check"></i> Approve
                    </button>
                    <button class="btn btn-sm btn-danger deny-btn" data-player-id="${req.playerId}">
                        <i class="fas fa-times"></i> Deny
                    </button>
                </div>
            </div>
        `).join('');
    } else {
        pendingSection.style.display = 'none';
    }
    
    // Render players grid
    if (state.players.length === 0) {
        playersGrid.style.display = 'none';
        noPlayers.style.display = 'block';
    } else {
        playersGrid.style.display = 'grid';
        noPlayers.style.display = 'none';
        
        playersGrid.innerHTML = state.players.map(player => {
            const modeClass = player.isPending ? 'pending' : player.mode;
            
            return `
                <div class="player-card">
                    <div class="player-info">
                        <span class="mode-dot ${modeClass}"></span>
                        <span class="player-name">${escapeHtml(player.name)}</span>
                    </div>
                    <div class="player-status">${player.isPending ? 'Pending Approval' : (player.mode === 'digital' ? 'Digital' : 'Manual')}</div>
                </div>
            `;
        }).join('');
    }
    
    // Attach event listeners
    attachPlayerModeListeners();
}
```

### Event Listeners

```javascript
function attachPlayerModeListeners() {
    // Approve buttons
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const playerId = btn.dataset.playerId;
            sendMessage({
                type: 'playerModeAction',
                action: 'approve',
                playerId: playerId
            });
        });
    });
    
    // Deny buttons
    document.querySelectorAll('.deny-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const playerId = btn.dataset.playerId;
            sendMessage({
                type: 'playerModeAction',
                action: 'deny',
                playerId: playerId
            });
        });
    });
}
}

// Utility function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

---

## Code Organization

**Follow DLA's modular structure:**

- `constants.js` - No changes needed (colors already defined)
- `state.js` - Add `isGM`, `globalOverride`, `players`, `pendingRequests`
- `websocket.js` - Add `playerModesUpdate` message handler, route to UI module
- `ui/player-modes.js` - New file containing:
  - `renderPlayerModes()`
  - `attachPlayerModeListeners()`
  - `handlePlayerModesUpdate()`

---

## Testing Checklist

1. **Display:**
   - [ ] Legend shows Digital/Manual/Pending dots with correct colors
   - [ ] Players grid displays all connected players
   - [ ] "No players connected" shows when no players
   - [ ] Mode dots show correct color per player mode

2. **GM-only features:**
   - [ ] Pending Requests section only visible to GM
   - [ ] Approve/Deny buttons work and send correct message to DLC

3. **Player view (non-GM):**
   - [ ] No Approve/Deny buttons visible
   - [ ] Can still see all players and their modes (read-only)

4. **Real-time updates:**
   - [ ] UI updates when `playerModesUpdate` message received
   - [ ] Mode changes reflect immediately
   - [ ] Pending status changes reflect immediately

---

## DLC Changes Required

DLC needs to:
1. Send `playerModesUpdate` message to DLA when connection established
2. Send `playerModesUpdate` message whenever player modes change
3. Handle incoming `playerModeAction` messages from DLA and execute the approve/deny/revoke actions

I will implement these DLC changes after DLA confirms the spec.
