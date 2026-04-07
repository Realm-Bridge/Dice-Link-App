/**
 * Application State Management
 * Centralized state with getter/setter functions for controlled access
 */

// Private state object
const _state = {
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
    reconnectTimeout: null,
    // Camera state (Phase 3)
    cameraList: [],
    cameraStreamActive: false,
    // Two-phase communication state
    pendingDiceRequest: null,
    // Dice tray state
    diceTrayDice: { 4: 0, 6: 0, 8: 0, 10: 0, 12: 0, 20: 0, 100: 0 },
    diceTrayModifier: 0,
    diceTrayAdvMode: 'normal'
};

// ============================================================================
// State Getters
// ============================================================================

function getState() {
    return _state;
}

function getConnection() {
    return { ws: _state.ws, connected: _state.connected };
}

function getCurrentRoll() {
    return _state.currentRoll;
}

function getSettings() {
    return { ..._state.settings };
}

function getPendingDiceRequest() {
    return _state.pendingDiceRequest;
}

function getDiceTrayState() {
    return {
        dice: { ..._state.diceTrayDice },
        modifier: _state.diceTrayModifier,
        advMode: _state.diceTrayAdvMode
    };
}

function getCameraList() {
    return [..._state.cameraList];
}

function getWebSocket() {
    return _state.ws;
}

function isConnected() {
    return _state.connected;
}

function isReconnecting() {
    return _state.reconnecting;
}

// ============================================================================
// State Setters
// ============================================================================

function setWebSocket(ws) {
    _state.ws = ws;
}

function setConnected(connected) {
    _state.connected = connected;
}

function setCurrentRoll(roll) {
    _state.currentRoll = roll;
}

function setSelectedButton(button) {
    _state.selectedButton = button;
}

function setConfigValue(field, value) {
    _state.configValues[field] = value;
}

function clearConfigValues() {
    _state.configValues = {};
}

function setDiceResult(index, value) {
    if (!_state.diceResults[index]) {
        _state.diceResults[index] = {};
    }
    _state.diceResults[index].value = value;
}

function clearDiceResults() {
    _state.diceResults = [];
}

function setSettings(settings) {
    _state.settings = { ..._state.settings, ...settings };
}

function setPendingDiceRequest(request) {
    _state.pendingDiceRequest = request;
}

function setReconnectAttempts(attempts) {
    _state.reconnectAttempts = attempts;
}

function setReconnecting(reconnecting) {
    _state.reconnecting = reconnecting;
}

function setReconnectTimeout(timeout) {
    _state.reconnectTimeout = timeout;
}

function setCameraList(cameras) {
    _state.cameraList = [...cameras];
}

function setCameraStreamActive(active) {
    _state.cameraStreamActive = active;
}

function setDiceTrayState(dice, modifier, advMode) {
    if (dice) _state.diceTrayDice = { ...dice };
    if (modifier !== undefined) _state.diceTrayModifier = modifier;
    if (advMode) _state.diceTrayAdvMode = advMode;
}

function updateDiceTrayDie(die, count) {
    _state.diceTrayDice[die] = Math.max(0, count);
}

function updateDiceTrayModifier(modifier) {
    _state.diceTrayModifier = modifier;
}

function updateDiceTrayAdvMode(mode) {
    _state.diceTrayAdvMode = mode;
}

function resetDiceTray() {
    _state.diceTrayDice = { 4: 0, 6: 0, 8: 0, 10: 0, 12: 0, 20: 0, 100: 0 };
    _state.diceTrayModifier = 0;
    _state.diceTrayAdvMode = 'normal';
}

function resetRollState() {
    _state.currentRoll = null;
    _state.selectedButton = null;
    _state.configValues = {};
    _state.diceResults = [];
    _state.pendingDiceRequest = null;
}
