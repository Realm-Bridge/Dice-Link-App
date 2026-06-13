function loadSettings() {
    try {
        const stored = localStorage.getItem(STORAGE_KEYS.SETTINGS);
        if (stored) {
            setSettings(JSON.parse(stored));
        }
    } catch (e) {
        // use defaults
    }
}

function initSettingsUI() {
    document.querySelectorAll('#settings-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (window.pyqtBridge && window.pyqtBridge.openSettings) {
                window.pyqtBridge.openSettings();
            }
        });
    });
}
