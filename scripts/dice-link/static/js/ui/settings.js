(function () {

    function init() {
        document.querySelectorAll('#settings-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                if (window.pyqtBridge && window.pyqtBridge.openSettings) {
                    window.pyqtBridge.openSettings();
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
