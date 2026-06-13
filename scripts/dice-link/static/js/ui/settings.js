function initSettingsUI() {
    document.querySelectorAll('#settings-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (window.pyqtBridge && window.pyqtBridge.openSettings) {
                window.pyqtBridge.openSettings();
            }
        });
    });
}
