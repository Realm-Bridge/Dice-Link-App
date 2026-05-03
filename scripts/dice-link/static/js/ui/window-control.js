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

        // Connect button
        const connectBtn = document.getElementById('connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                console.log('[WindowControl] Connect button clicked');
                pyqtBridge.openConnectionDialog();
            });
        }
        
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
        let isResizing = false;

        titleBar.addEventListener('mousedown', (e) => {
            if (e.target.closest('button')) return;
            isDragging = true;
            pyqtBridge.startDrag(e.screenX, e.screenY);
        });

        // Resize grip - injected into the page so it renders inside the web content
        const resizeGrip = document.createElement('div');
        resizeGrip.id = 'resize-grip';
        resizeGrip.style.cssText = [
            'position:fixed',
            'bottom:0',
            'right:0',
            'width:16px',
            'height:16px',
            'cursor:nwse-resize',
            'z-index:9999',
            'background:linear-gradient(135deg, transparent 50%, rgba(111,46,154,0.5) 50%)'
        ].join(';');
        document.body.appendChild(resizeGrip);

        resizeGrip.addEventListener('mousedown', (e) => {
            isResizing = true;
            pyqtBridge.startResize(e.screenX, e.screenY);
            e.preventDefault();
            e.stopPropagation();
        });

        // Combined mousemove and mouseup for both drag and resize
        document.addEventListener('mousemove', (e) => {
            if (isDragging) pyqtBridge.doDrag(e.screenX, e.screenY);
            if (isResizing) pyqtBridge.doResize(e.screenX, e.screenY);
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            isResizing = false;
        });

        // Reset drag/resize state when Windows takes over the mouse (e.g. during snap)
        window.addEventListener('blur', () => {
            isDragging = false;
            isResizing = false;
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


