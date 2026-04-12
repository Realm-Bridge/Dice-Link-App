/**
 * Window Control Handler for Frameless PyQt5 Window
 * Handles minimize, maximize, and close button functionality via PyQt QWebChannel
 */

function initWindowControls() {
    const minimizeBtn = document.getElementById('minimize-btn');
    const maximizeBtn = document.getElementById('maximize-btn');
    const closeBtn = document.getElementById('close-btn');
    
    if (!minimizeBtn || !maximizeBtn || !closeBtn) {
        console.warn('[WindowControl] Window control buttons not found in DOM');
        return;
    }
    
    // Wait for the PyQt WebChannel to be available
    if (typeof qt === 'undefined') {
        console.warn('[WindowControl] PyQt WebChannel not available, retrying...');
        setTimeout(initWindowControls, 500);
        return;
    }
    
    // Get the window controller from PyQt bridge
    qt.webChannelTransport.onmessage = function() {};
    
    new QWebChannel(qt.webChannelTransport, function(channel) {
        const pyqtBridge = channel.objects.pyqtBridge;
        
        if (!pyqtBridge) {
            console.warn('[WindowControl] PyQt bridge object not found');
            return;
        }
        
        minimizeBtn.addEventListener('click', () => {
            console.log('[WindowControl] Minimize button clicked');
            pyqtBridge.minimize();
        });
        
        maximizeBtn.addEventListener('click', () => {
            console.log('[WindowControl] Maximize button clicked');
            pyqtBridge.maximize();
        });
        
        closeBtn.addEventListener('click', () => {
            console.log('[WindowControl] Close button clicked');
            pyqtBridge.close();
        });
        
        console.log('[WindowControl] Window controls initialized successfully');
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWindowControls);
} else {
    initWindowControls();
}

