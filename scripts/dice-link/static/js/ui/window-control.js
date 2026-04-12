/**
 * Window Control Handler for Frameless PyQt5 Window
 * Handles minimize and close button functionality via PyQt QWebChannel
 * Also handles window dragging from the title bar
 */

function initWindowControls() {
    const titleBar = document.getElementById('title-bar');
    const minimizeBtn = document.getElementById('minimize-btn');
    const closeBtn = document.getElementById('close-btn');
    
    if (!titleBar || !minimizeBtn || !closeBtn) {
        console.warn('[WindowControl] Window control elements not found in DOM');
        return;
    }
    
    // Wait for the PyQt WebChannel to be available
    if (typeof qt === 'undefined') {
        console.warn('[WindowControl] PyQt WebChannel not available, retrying...');
        setTimeout(initWindowControls, 500);
        return;
    }
    
    // Get the window controller from PyQt bridge
    new QWebChannel(qt.webChannelTransport, function(channel) {
        const pyqtBridge = channel.objects.pyqtBridge;
        
        if (!pyqtBridge) {
            console.warn('[WindowControl] PyQt bridge object not found');
            return;
        }
        
        // Expose pyqtBridge globally so other elements can use it
        window.pyqtBridge = pyqtBridge;
        
        // Minimize button
        minimizeBtn.addEventListener('click', () => {
            console.log('[WindowControl] Minimize button clicked');
            pyqtBridge.minimize();
        });
        
        // Close button
        closeBtn.addEventListener('click', () => {
            console.log('[WindowControl] Close button clicked');
            pyqtBridge.close();
        });
        
        // Window dragging from title bar
        let isDragging = false;
        
        titleBar.addEventListener('mousedown', (e) => {
            // Ignore clicks on buttons
            if (e.target.closest('button')) {
                return;
            }
            isDragging = true;
            console.log('[WindowControl] Drag started at', e.clientX, e.clientY);
            pyqtBridge.startDrag(e.clientX, e.clientY);
        });
        
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                pyqtBridge.doDrag(e.clientX, e.clientY);
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                console.log('[WindowControl] Drag ended');
                isDragging = false;
            }
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


