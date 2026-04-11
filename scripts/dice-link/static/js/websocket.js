/**
 * WebSocket Connection Management
 * Handles connection, reconnection, message routing
 */

/**
 * Initialize WebSocket connection
 */
function initWebSocket() {
    // Clear any existing reconnect timeout
    const reconnectTimeout = getState().reconnectTimeout;
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        setReconnectTimeout(null);
    }
    
    const settings = getSettings();
    const wsUrl = `ws://${settings.host}:${settings.port}/ws/ui`;
    
    debugLog(`Connecting to WebSocket: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    setWebSocket(ws);
    
    ws.onopen = () => {
        debugLog('WebSocket connected to server');
        setConnected(true);
        setReconnectAttempts(0);
        setReconnecting(false);
        updateConnectionUI();
    };
    
    ws.onclose = () => {
        debugLog('WebSocket disconnected');
        setConnected(false);
        handleReconnection();
    };
    
    ws.onerror = (error) => {
        debugError('WebSocket error', error);
    };
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleMessage(message);
        } catch (error) {
            debugError('Failed to parse WebSocket message', error);
        }
    };
}

/**
 * Handle reconnection with exponential backoff
 */
function handleReconnection() {
    const reconnectAttempts = getState().reconnectAttempts;
    
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        debugLog(`Max reconnect attempts (${MAX_RECONNECT_ATTEMPTS}) reached`);
        setReconnecting(false);
        updateConnectionUI(true); // Show reconnect button
        return;
    }
    
    setReconnecting(true);
    setReconnectAttempts(reconnectAttempts + 1);
    
    // Exponential backoff: 2s, 4s, 8s, 16s, 32s
    const delay = BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts);
    debugLog(`Reconnecting in ${formatTime(delay)}... (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
    
    updateConnectionUI();
    
    const timeout = setTimeout(() => {
        initWebSocket();
    }, delay);
    
    setReconnectTimeout(timeout);
}

/**
 * Manual reconnect triggered by user
 */
function manualReconnect() {
    debugLog('User triggered manual reconnect');
    setReconnectAttempts(0);
    setReconnecting(false);
    initWebSocket();
}

/**
 * Send a message to the server
 */
function sendMessage(message) {
    const { ws, connected } = getConnection();
    
    if (!ws || !connected) {
        debugError('Cannot send message: WebSocket not connected', message);
        return;
    }
    
    try {
        const json = JSON.stringify(message);
        ws.send(json);
        debugLog(`Sent message: ${message.type}`, message);
    } catch (error) {
        debugError('Failed to send message', error);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleMessage(message) {
    debugLog(`Received message: ${message.type}`);
    
    switch (message.type) {
        case 'debug':
            // Debug messages from backend
            debugLog(`[Backend] ${message.message}`);
            break;
            
        case 'status':
            handleStatusUpdate(message.data);
            break;
            
        case 'connectionStatus':
            handleConnectionStatus(message.connected, message.playerName);
            break;
            
        case 'rollRequest':
            handleRollRequest(message);
            break;
            
        case 'diceRequest':
            handleDiceRequest(message);
            break;
            
        case 'buttonSelectAck':
            if (!message.success) {
                debugError('Failed to send button selection');
            }
            break;
            
        case 'rollComplete':
            debugLog('Roll completed successfully');
            break;
            
        case 'rollCancelled':
            debugLog('Roll cancelled');
            break;
            
        case 'submitResultAck':
            if (!message.success) {
                debugError('Failed to submit results');
            } else {
                debugLog('Results submitted successfully');
            }
            break;
            
        case 'cancelRollAck':
            if (!message.success) {
                debugError('Failed to cancel roll');
            }
            break;
            
        case 'playerModesUpdate':
            updatePlayerModes(message.data);
            break;
            
        // Camera messages (Phase 3)
        case 'cameraFrame':
            // handleCameraFrame(message.frame);
            break;
            
        case 'cameraStreamStatus':
            setCameraStreamActive(message.active);
            debugLog(`Camera stream ${message.active ? 'started' : 'stopped'}`);
            break;
            
        default:
            debugLog(`Unknown message type: ${message.type}`, message);
    }
}

/**
 * Handle initial status update
 */
function handleStatusUpdate(data) {
    handleConnectionStatus(data.connected, data.playerName);
    
    if (data.currentRoll) {
        handleRollRequest(data.currentRoll);
    }
}

/**
 * Update connection status and UI
 */
function handleConnectionStatus(connected, playerName) {
    setConnected(connected);
    updateConnectionUI();
    
    const elements = cacheElements();
    
    if (connected) {
        if (elements.connectionStatus) {
            elements.connectionStatus.classList.remove('disconnected');
            elements.connectionStatus.classList.add('connected');
            if (elements.connectionText) {
                elements.connectionText.textContent = playerName ? `Connected: ${playerName}` : 'Connected';
            }
        }
        
        // Hide waiting state when connected
        if (elements.waitingState) {
            elements.waitingState.classList.add('hidden');
        }
        
        // Show Roll Window idle state if no active roll
        if (!getCurrentRoll()) {
            updateRollWindow('idle');
        }
    } else {
        if (elements.connectionStatus) {
            elements.connectionStatus.classList.remove('connected');
            elements.connectionStatus.classList.add('disconnected');
            if (elements.connectionText) {
                elements.connectionText.textContent = 'Disconnected';
            }
        }
    }
}

/**
 * Update connection UI elements
 */
function updateConnectionUI(showReconnectButton = false) {
    const { connected, reconnecting } = getState();
    const elements = cacheElements();
    const statusElement = elements.connectionStatus;
    const statusText = elements.connectionText;
    
    if (!statusElement || !statusText) return;
    
    if (connected) {
        statusElement.classList.remove('disconnected', 'reconnecting');
        statusElement.classList.add('connected');
    } else if (reconnecting) {
        statusElement.classList.remove('connected', 'disconnected');
        statusElement.classList.add('reconnecting');
        const attempts = getState().reconnectAttempts;
        statusText.textContent = `Reconnecting (${attempts}/${MAX_RECONNECT_ATTEMPTS})...`;
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
    }
}
