(function () {

    function buildPanel() {
        const overlay = document.createElement('div');
        overlay.id        = 'settings-overlay';
        overlay.className = 'settings-overlay';
        overlay.innerHTML = `
            <div id="settings-panel" class="settings-panel">
                <div class="settings-header">
                    <h2><i class="fas fa-cog"></i> Settings</h2>
                    <button id="settings-close" class="settings-close-btn" title="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="settings-body">
                    <nav class="settings-nav">
                        <button class="settings-nav-btn active" data-section="account">
                            <i class="fas fa-user"></i><span>Account</span>
                        </button>
                        <button class="settings-nav-btn" data-section="notifications">
                            <i class="fas fa-bell"></i><span>Notifications</span>
                        </button>
                    </nav>
                    <div class="settings-content">

                        <div class="settings-section active" id="settings-section-account">
                            <div class="settings-section-title">Account</div>
                            <div class="settings-field">
                                <label>Manage Account</label>
                                <p class="settings-help-text">Change your email, password, or subscription on the Realm Bridge website.</p>
                                <a href="#" class="settings-link" id="settings-account-link">
                                    <i class="fas fa-external-link-alt"></i> realmbridge.co.uk
                                </a>
                            </div>
                            <div class="settings-field settings-toggle-field">
                                <div class="settings-toggle-label">
                                    <label>Record dice roll history</label>
                                    <p class="settings-help-text">Stores your roll results locally on this machine for stats tracking.</p>
                                </div>
                                <label class="settings-toggle">
                                    <input type="checkbox" id="settings-record-rolls" checked>
                                    <span class="settings-toggle-slider"></span>
                                </label>
                            </div>
                        </div>

                        <div class="settings-section" id="settings-section-notifications">
                            <div class="settings-section-title">Notifications</div>
                            <p class="settings-coming-soon">
                                <i class="fas fa-bell-slash"></i>
                                Notification settings are coming soon.
                            </p>
                        </div>

                    </div>
                </div>
            </div>`;
        document.body.appendChild(overlay);
    }

    // Tracks the latest zoom injected by Python. Updated on every window resize.
    let _currentZoom = window.DLA_ZOOM_FACTOR || 1;

    function _applyScale(panel, zoom) {
        // Scale DOWN on large windows so the panel doesn't overflow; never scale UP.
        const scale = Math.min(1 / zoom, 1);
        panel.style.transform = scale < 1 ? `scale(${scale})` : '';
        panel.style.transformOrigin = 'center center';
    }

    function open() {
        document.getElementById('settings-overlay')?.classList.add('open');
        const panel = document.getElementById('settings-panel');
        if (panel) {
            _applyScale(panel, _currentZoom);
        }
        loadFromApi();
    }

    function close() {
        document.getElementById('settings-overlay')?.classList.remove('open');
    }

    async function loadFromApi() {
        try {
            const res    = await fetch('/api/config');
            const config = await res.json();
            const toggle = document.getElementById('settings-record-rolls');
            if (toggle) toggle.checked = config.record_rolls !== false;
        } catch (e) {}
    }

    async function saveConfig(patch) {
        try {
            await fetch('/api/config', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(patch),
            });
        } catch (e) {}
    }

    function init() {
        buildPanel();

        // Keep _currentZoom in sync and re-apply scale if the panel is open during a resize.
        window.addEventListener('dla-zoom-changed', function(e) {
            _currentZoom = e.detail.zoom;
            const overlay = document.getElementById('settings-overlay');
            const panel   = document.getElementById('settings-panel');
            if (panel && overlay && overlay.classList.contains('open')) {
                _applyScale(panel, _currentZoom);
            }
        });

        document.querySelectorAll('#settings-btn').forEach(btn =>
            btn.addEventListener('click', open)
        );

        document.getElementById('settings-close')?.addEventListener('click', close);

        document.getElementById('settings-overlay')?.addEventListener('click', e => {
            if (e.target.id === 'settings-overlay') close();
        });

        document.querySelectorAll('.settings-nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.settings-nav-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(`settings-section-${btn.dataset.section}`)?.classList.add('active');
            });
        });

        document.getElementById('settings-account-link')?.addEventListener('click', e => {
            e.preventDefault();
            if (window.pyqtBridge?.openUrl) {
                window.pyqtBridge.openUrl('https://realmbridge.co.uk/');
            }
        });

        document.getElementById('settings-record-rolls')?.addEventListener('change', e => {
            saveConfig({ record_rolls: e.target.checked });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
