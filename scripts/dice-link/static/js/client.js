/**
 * Dice Link - Browser WebSocket Client
 * Handles communication with the FastAPI backend and UI updates
 * Phase 2: Enhanced UI with SVG dice icons and settings panel
 */

// Dice value ranges for validation
const DICE_RANGES = {
    d4: { min: 1, max: 4 },
    d6: { min: 1, max: 6 },
    d8: { min: 1, max: 8 },
    d10: { min: 0, max: 9 },
    d12: { min: 1, max: 12 },
    d20: { min: 1, max: 20 },
    d100: { min: 1, max: 100 }
};

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
    
    if (value !== null && value !== undefined) {
        // Return numbered icon if it exists (d100 only has blank)
        if (type === 'd100') {
            return `/static/DLC Dice/${folder}/${type}-blank.svg`;
        }
        // Numbered files have format "d20 - Outline 1.svg"
        return `/static/DLC Dice/${folder}/${type} - Outline ${value}.svg`;
    }
    return `/static/DLC Dice/${folder}/${type}-blank.svg`;
}

// Default settings
const DEFAULT_SETTINGS = {
    host: 'localhost',
    port: 8765,
    theme: 'dark'
};

// Connection constants
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 2000; // 2 seconds

// Application state
const state = {
    ws: null,
    connected: false,
    currentRoll: null,
    selectedButton: null,
    configValues: {},
    diceResults: [],
    settings: { ...DEFAULT_SETTINGS },
    // Connection state
    reconnectAttempts: 0,
    reconnecting: false,
    reconnectTimeout: null
};

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connection-status'),
    statusText: document.querySelector('.status-text'),
    waitingState: document.getElementById('waiting-state'),
    rollPanel: document.getElementById('roll-panel'),
    diceEntryPanel: document.getElementById('dice-entry-panel'),
    completeState: document.getElementById('complete-state'),
    rollTitle: document.getElementById('roll-title'),
    rollSubtitle: document.getElementById('roll-subtitle'),
    diceDisplay: document.getElementById('dice-display'),
    rollFormula: document.getElementById('roll-formula'),
    configSection: document.getElementById('config-section'),
    configFields: document.getElementById('config-fields'),
    actionButtons: document.getElementById('action-buttons'),
    selectedAction: document.getElementById('selected-action'),
    diceInputs: document.getElementById('dice-inputs'),
    submitResults: document.getElementById('submit-results'),
    backToConfig: document.getElementById('back-to-config'),
    cancelRoll: document.getElementById('cancel-roll'),
    completeIcon: document.getElementById('complete-icon'),
    completeTitle: document.getElementById('complete-title'),
    completeMessage: document.getElementById('complete-message')
};

/**
 * Initialize WebSocket connection
 */
function initWebSocket() {
    // Clear any existing reconnect timeout
    if (state.reconnectTimeout) {
        clearTimeout(state.reconnectTimeout);
        state.reconnectTimeout = null;
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/ui`;
    
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
        console.log('WebSocket connected to server');
        // Reset reconnection state on successful connect
        state.reconnectAttempts = 0;
        state.reconnecting = false;
        updateConnectionUI();
    };
    
    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        state.connected = false;
        handleReconnection();
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleMessage(message);
    };
}

/**
 * Handle reconnection with exponential backoff
 */
function handleReconnection() {
    if (state.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        // Max attempts reached
        state.reconnecting = false;
        updateConnectionUI(true); // Show reconnect button
        return;
    }
    
    state.reconnecting = true;
    state.reconnectAttempts++;
    
    // Exponential backoff: 2s, 4s, 8s, 16s, 32s
    const delay = BASE_RECONNECT_DELAY * Math.pow(2, state.reconnectAttempts - 1);
    
    updateConnectionUI();
    
    state.reconnectTimeout = setTimeout(() => {
        initWebSocket();
    }, delay);
}

/**
 * Manual reconnect triggered by user
 */
function manualReconnect() {
    state.reconnectAttempts = 0;
    state.reconnecting = false;
    initWebSocket();
}

/**
 * Update connection status UI
 */
function updateConnectionUI(showReconnectButton = false) {
    const statusElement = document.getElementById('connection-status');
    const statusText = statusElement?.querySelector('.status-text');
    
    if (!statusElement || !statusText) return;
    
    if (state.connected) {
        statusElement.classList.remove('disconnected', 'reconnecting');
        statusElement.classList.add('connected');
        statusText.textContent = 'Connected';
    } else if (state.reconnecting) {
        statusElement.classList.remove('connected', 'disconnected');
        statusElement.classList.add('reconnecting');
        statusText.textContent = `Reconnecting (${state.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`;
    } else if (showReconnectButton) {
        statusElement.classList.remove('connected', 'reconnecting');
        statusElement.classList.add('disconnected');
        statusText.innerHTML = `Disconnected <button id="reconnect-btn" class="reconnect-btn">Reconnect</button>`;
        
        // Add event listener to reconnect button
        const reconnectBtn = document.getElementById('reconnect-btn');
        if (reconnectBtn) {
            reconnectBtn.addEventListener('click', manualReconnect);
        }
    } else {
        statusElement.classList.remove('connected', 'reconnecting');
        statusElement.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleMessage(message) {
    console.log('Received message:', message.type, message);
    
    switch (message.type) {
        case 'status':
            handleStatusUpdate(message.data);
            break;
        case 'connectionStatus':
            updateConnectionStatus(message.connected, message.playerName);
            break;
        case 'rollRequest':
            handleRollRequest(message.data);
            break;
        case 'rollComplete':
            showCompleteState('success', 'Roll Submitted', 'Results sent to Foundry VTT');
            break;
        case 'rollCancelled':
            showCompleteState('cancelled', 'Roll Cancelled', 'Waiting for next roll...');
            break;
        case 'submitResultAck':
            if (!message.success) {
                alert('Failed to submit results. Please try again.');
            }
            break;
        case 'cancelRollAck':
            if (!message.success) {
                alert('Failed to cancel roll.');
            }
            break;
        default:
            console.warn('Unknown message type:', message.type);
    }
}

/**
 * Handle initial status update
 */
function handleStatusUpdate(data) {
    updateConnectionStatus(data.connected, data.playerName);
    
    if (data.currentRoll) {
        handleRollRequest(data.currentRoll);
    }
}

/**
 * Update connection status display
 */
function updateConnectionStatus(connected, playerName) {
    state.connected = connected;
    
    if (connected) {
        elements.connectionStatus.classList.remove('disconnected');
        elements.connectionStatus.classList.add('connected');
        elements.statusText.textContent = playerName ? `Connected: ${playerName}` : 'Connected';
    } else {
        elements.connectionStatus.classList.remove('connected');
        elements.connectionStatus.classList.add('disconnected');
        elements.statusText.textContent = 'Disconnected';
        
        // Show waiting state if disconnected and no active roll
        if (!state.currentRoll) {
            showPanel('waiting');
        }
    }
}

/**
 * Handle incoming roll request
 */
function handleRollRequest(data) {
    state.currentRoll = data;
    state.selectedButton = null;
    state.configValues = {};
    state.diceResults = [];
    
    // Populate roll header
    elements.rollTitle.textContent = data.roll.title || 'Roll';
    elements.rollSubtitle.textContent = data.roll.subtitle || '';
    
    // Render dice display
    renderDiceDisplay(data.roll.dice);
    elements.rollFormula.textContent = data.roll.formula || '';
    
    // Render config fields
    renderConfigFields(data.config?.fields || []);
    
    // Render action buttons
    renderActionButtons(data.buttons || []);
    
    // Show roll panel and cancel button
    showPanel('roll');
    elements.cancelRoll.classList.remove('hidden');
}

/**
 * Render dice display with SVG icons
 */
function renderDiceDisplay(dice) {
    elements.diceDisplay.innerHTML = '';
    
    if (!dice || dice.length === 0) {
        elements.diceDisplay.innerHTML = '<p class="text-muted">No dice specified</p>';
        return;
    }
    
    dice.forEach(die => {
        const dieElement = document.createElement('div');
        dieElement.className = 'dice-item';
        const iconPath = getDiceIconPath(die.type);
        dieElement.innerHTML = `
            <img src="${iconPath}" alt="${die.type}" class="dice-icon" title="${die.type}">
            <span class="dice-count">${die.count > 1 ? `x${die.count}` : ''}</span>
        `;
        elements.diceDisplay.appendChild(dieElement);
    });
}

/**
 * Render configuration fields
 */
function renderConfigFields(fields) {
    elements.configFields.innerHTML = '';
    
    if (!fields || fields.length === 0) {
        elements.configSection.classList.add('hidden');
        return;
    }
    
    elements.configSection.classList.remove('hidden');
    
    fields.forEach(field => {
        const fieldElement = document.createElement('div');
        fieldElement.className = 'config-field';
        
        // Initialize config value
        state.configValues[field.name] = field.selected || field.value || '';
        
        let inputHtml = '';
        
        switch (field.type) {
            case 'select':
                const options = (field.options || []).map(opt => 
                    `<option value="${opt.value}" ${opt.value === field.selected ? 'selected' : ''}>${opt.label}</option>`
                ).join('');
                inputHtml = `<select id="config-${field.name}" data-field="${field.name}">${options}</select>`;
                break;
            
            case 'number':
                inputHtml = `<input type="number" id="config-${field.name}" data-field="${field.name}" 
                    value="${field.value || ''}" 
                    ${field.min !== undefined ? `min="${field.min}"` : ''} 
                    ${field.max !== undefined ? `max="${field.max}"` : ''}>`;
                break;
            
            case 'text':
            default:
                inputHtml = `<input type="text" id="config-${field.name}" data-field="${field.name}" 
                    value="${field.value || ''}" placeholder="${field.placeholder || ''}">`;
                break;
        }
        
        fieldElement.innerHTML = `
            <label for="config-${field.name}">${field.label}</label>
            ${inputHtml}
        `;
        
        elements.configFields.appendChild(fieldElement);
    });
    
    // Add change listeners
    elements.configFields.querySelectorAll('select, input').forEach(input => {
        input.addEventListener('change', (e) => {
            const fieldName = e.target.dataset.field;
            state.configValues[fieldName] = e.target.value;
        });
    });
}

/**
 * Render action buttons
 */
function renderActionButtons(buttons) {
    elements.actionButtons.innerHTML = '';
    
    if (!buttons || buttons.length === 0) {
        // Default button if none specified
        buttons = [{ id: 'normal', label: 'Roll' }];
    }
    
    buttons.forEach(button => {
        const btnElement = document.createElement('button');
        btnElement.className = 'action-btn';
        btnElement.textContent = button.label;
        btnElement.dataset.buttonId = button.id;
        
        btnElement.addEventListener('click', () => {
            selectActionButton(button.id, button.label);
        });
        
        elements.actionButtons.appendChild(btnElement);
    });
}

/**
 * Select an action button and proceed to dice entry
 */
function selectActionButton(buttonId, buttonLabel) {
    state.selectedButton = buttonId;
    
    // Update visual selection
    elements.actionButtons.querySelectorAll('.action-btn').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.buttonId === buttonId);
    });
    
    // Show dice entry panel
    elements.selectedAction.textContent = buttonLabel;
    renderDiceInputs();
    showPanel('dice-entry');
}

/**
 * Render dice input fields with SVG icons
 */
function renderDiceInputs() {
    elements.diceInputs.innerHTML = '';
    state.diceResults = [];
    
    const dice = state.currentRoll?.roll?.dice || [];
    
    dice.forEach((die, dieIndex) => {
        for (let i = 0; i < die.count; i++) {
            const inputIndex = state.diceResults.length;
            state.diceResults.push({ type: die.type, value: null });
            
            const range = DICE_RANGES[die.type] || { min: 1, max: 20 };
            const iconPath = getDiceIconPath(die.type);
            
            const inputGroup = document.createElement('div');
            inputGroup.className = 'dice-input-group';
            inputGroup.innerHTML = `
                <img src="${iconPath}" alt="${die.type}" class="dice-input-icon" data-index="${inputIndex}" title="${die.type}">
                <input type="number" 
                    class="dice-input-field" 
                    data-index="${inputIndex}"
                    data-type="${die.type}"
                    min="${range.min}" 
                    max="${range.max}"
                    placeholder="${range.min}-${range.max}">
                <span class="dice-input-range">(${range.min}-${range.max})</span>
            `;
            
            elements.diceInputs.appendChild(inputGroup);
        }
    });
    
    // Add input listeners
    elements.diceInputs.querySelectorAll('.dice-input-field').forEach(input => {
        input.addEventListener('input', handleDiceInput);
    });
    
    // Focus first input
    const firstInput = elements.diceInputs.querySelector('.dice-input-field');
    if (firstInput) {
        firstInput.focus();
    }
    
    updateSubmitButton();
}

/**
 * Handle dice input change - updates state, validation, and dice icon
 */
function handleDiceInput(e) {
    const input = e.target;
    const index = parseInt(input.dataset.index);
    const type = input.dataset.type;
    const value = input.value === '' ? null : parseInt(input.value);
    const range = DICE_RANGES[type] || { min: 1, max: 20 };
    
    // Update state
    state.diceResults[index] = { type, value };
    
    // Find the corresponding dice icon and update it based on value
    const icon = document.querySelector(`.dice-input-icon[data-index="${index}"]`);
    if (icon) {
        const isValid = value !== null && value >= range.min && value <= range.max;
        // For now just use the blank icon - numbered icons would require more SVGs
        // In the future, swap to numbered SVG: getDiceIconPath(type, isValid ? value : null)
        if (isValid) {
            icon.classList.add('has-value');
        } else {
            icon.classList.remove('has-value');
        }
    }
    
    // Validate and update styling
    if (value === null) {
        input.classList.remove('valid', 'invalid');
    } else if (value >= range.min && value <= range.max) {
        input.classList.remove('invalid');
        input.classList.add('valid');
    } else {
        input.classList.remove('valid');
        input.classList.add('invalid');
    }
    
    updateSubmitButton();
}

/**
 * Update submit button state
 */
function updateSubmitButton() {
    const allValid = state.diceResults.every(result => {
        if (result.value === null) return false;
        const range = DICE_RANGES[result.type] || { min: 1, max: 20 };
        return result.value >= range.min && result.value <= range.max;
    });
    
    elements.submitResults.disabled = !allValid;
}

/**
 * Submit dice results
 */
function submitResults() {
    if (!state.currentRoll || !state.selectedButton) return;
    
    // Build config changes (compare with original values)
    const configChanges = {};
    const originalFields = state.currentRoll.config?.fields || [];
    
    originalFields.forEach(field => {
        const originalValue = field.selected || field.value || '';
        const currentValue = state.configValues[field.name] || '';
        
        if (originalValue !== currentValue) {
            configChanges[field.name] = currentValue;
        }
    });
    
    // Build results array
    const results = state.diceResults.map(r => ({
        type: r.type,
        value: r.value
    }));
    
    // Check if this is a test roll (ID starts with "test-")
    if (state.currentRoll.id && state.currentRoll.id.startsWith('test-')) {
        // For test rolls, just show success without sending to Foundry
        const totalResult = results.reduce((sum, r) => sum + r.value, 0);
        showCompleteState('success', 'Test Roll Complete!', 
            `You rolled: ${results.map(r => r.type + '=' + r.value).join(', ')} (Total: ${totalResult})`);
        return;
    }
    
    // Send to server (for real Foundry VTT rolls)
    sendMessage({
        type: 'submitResult',
        rollId: state.currentRoll.id,
        buttonClicked: state.selectedButton,
        configChanges: configChanges,
        results: results
    });
}

/**
 * Cancel current roll
 */
function cancelRoll() {
    if (!state.currentRoll) return;
    
    // Check if this is a test roll (ID starts with "test-")
    if (state.currentRoll.id && state.currentRoll.id.startsWith('test-')) {
        // For test rolls, just go back to waiting state without sending a message
        showCompleteState('cancelled', 'Test Roll Cancelled', 'Ready for next test roll...');
        return;
    }
    
    // Send to server (for real Foundry VTT rolls)
    sendMessage({
        type: 'cancelRoll',
        rollId: state.currentRoll.id,
        reason: 'User cancelled'
    });
}

/**
 * Go back to config panel
 */
function backToConfig() {
    showPanel('roll');
}

/**
 * Show a specific panel
 */
function showPanel(panelName) {
    // Hide all panels
    elements.waitingState.classList.add('hidden');
    elements.rollPanel.classList.add('hidden');
    elements.diceEntryPanel.classList.add('hidden');
    elements.completeState.classList.add('hidden');
    
    // Show requested panel
    switch (panelName) {
        case 'waiting':
            elements.waitingState.classList.remove('hidden');
            elements.cancelRoll.classList.add('hidden');
            break;
        case 'roll':
            elements.rollPanel.classList.remove('hidden');
            elements.cancelRoll.classList.remove('hidden');
            break;
        case 'dice-entry':
            elements.diceEntryPanel.classList.remove('hidden');
            elements.cancelRoll.classList.remove('hidden');
            break;
        case 'complete':
            elements.completeState.classList.remove('hidden');
            elements.cancelRoll.classList.add('hidden');
            break;
    }
}

/**
 * Show completion state
 */
function showCompleteState(type, title, message) {
    state.currentRoll = null;
    state.selectedButton = null;
    
    elements.completeIcon.className = `complete-icon ${type}`;
    elements.completeTitle.textContent = title;
    elements.completeMessage.textContent = message;
    
    showPanel('complete');
    
    // Return to waiting state after delay
    setTimeout(() => {
        if (!state.currentRoll) {
            showPanel('waiting');
        }
    }, 3000);
}

/**
 * Send message to server
 */
function sendMessage(message) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(message));
    } else {
        console.error('WebSocket not connected');
    }
}

/**
 * Send a test roll - directly triggers the roll dialog without needing Foundry VTT
 * Uses the full Longsword Attack example from the spec document
 */
function sendTestRoll() {
    // Create a test roll matching the spec's Longsword Attack example
    const testRoll = {
        id: "test-" + Date.now(),
        timestamp: Date.now(),
        player: { id: "test-player", name: "Test Player" },
        roll: {
            title: "Longsword Attack",
            subtitle: "Melee Weapon Attack",
            formula: "1d20 + 5 + 1d4",
            dice: [
                { type: "d20", count: 1 },
                { type: "d4", count: 1 }
            ]
        },
        config: {
            fields: [
                {
                    name: "attackMode",
                    label: "Attack Mode",
                    type: "select",
                    options: [
                        { value: "oneHanded", label: "One-Handed" },
                        { value: "twoHanded", label: "Two-Handed" }
                    ],
                    selected: "oneHanded"
                },
                {
                    name: "rollMode",
                    label: "Roll Mode",
                    type: "select",
                    options: [
                        { value: "publicroll", label: "Public Roll" },
                        { value: "gmroll", label: "GM Only" },
                        { value: "blindroll", label: "Blind Roll" },
                        { value: "selfroll", label: "Self" }
                    ],
                    selected: "publicroll"
                },
                {
                    name: "situationalBonus",
                    label: "Situational Bonus",
                    type: "text",
                    value: ""
                }
            ]
        },
        buttons: [
            { id: "advantage", label: "Advantage" },
            { id: "normal", label: "Normal" },
            { id: "disadvantage", label: "Disadvantage" }
        ]
    };
    
    handleRollRequest(testRoll);
}

/**
 * Load settings from localStorage
 */
function loadSettings() {
    try {
        const saved = localStorage.getItem('dicelink-settings');
        if (saved) {
            const parsed = JSON.parse(saved);
            state.settings = { ...DEFAULT_SETTINGS, ...parsed };
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
    
    // Apply settings to UI
    const hostInput = document.getElementById('settings-host');
    const portInput = document.getElementById('settings-port');
    const themeSelect = document.getElementById('settings-theme');
    
    if (hostInput) hostInput.value = state.settings.host;
    if (portInput) portInput.value = state.settings.port;
    if (themeSelect) themeSelect.value = state.settings.theme;
}

/**
 * Save settings to localStorage
 */
function saveSettings() {
    const hostInput = document.getElementById('settings-host');
    const portInput = document.getElementById('settings-port');
    const themeSelect = document.getElementById('settings-theme');
    
    state.settings.host = hostInput?.value || DEFAULT_SETTINGS.host;
    state.settings.port = parseInt(portInput?.value) || DEFAULT_SETTINGS.port;
    state.settings.theme = themeSelect?.value || DEFAULT_SETTINGS.theme;
    
    try {
        localStorage.setItem('dicelink-settings', JSON.stringify(state.settings));
    } catch (e) {
        console.error('Failed to save settings:', e);
    }
    
    // Close settings panel
    closeSettings();
}

/**
 * Open settings panel
 */
function openSettings() {
    const overlay = document.getElementById('settings-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

/**
 * Close settings panel
 */
function closeSettings() {
    const overlay = document.getElementById('settings-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Initialize event listeners
 */
function initEventListeners() {
    elements.submitResults.addEventListener('click', submitResults);
    elements.backToConfig.addEventListener('click', backToConfig);
    elements.cancelRoll.addEventListener('click', cancelRoll);
    
    // Add test roll button listener if it exists
    const testRollBtn = document.getElementById('test-roll-btn');
    if (testRollBtn) {
        testRollBtn.addEventListener('click', sendTestRoll);
    }
    
    // Settings panel listeners
    const settingsBtn = document.getElementById('settings-btn');
    const settingsClose = document.getElementById('settings-close');
    const settingsSave = document.getElementById('settings-save');
    const settingsOverlay = document.getElementById('settings-overlay');
    
    if (settingsBtn) settingsBtn.addEventListener('click', openSettings);
    if (settingsClose) settingsClose.addEventListener('click', closeSettings);
    if (settingsSave) settingsSave.addEventListener('click', saveSettings);
    
    // Close settings when clicking outside the panel
    if (settingsOverlay) {
        settingsOverlay.addEventListener('click', (e) => {
            if (e.target === settingsOverlay) {
                closeSettings();
            }
        });
    }
}

/**
 * Initialize the application
 */
function init() {
    loadSettings();
    initEventListeners();
    initWebSocket();
}

// Start the app when DOM is ready
document.addEventListener('DOMContentLoaded', init);
